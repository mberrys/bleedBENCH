"""FFC ResNet generator (LaMa, Suvorov et al. 2022; Apache-2.0), re-implemented to load the
big-LaMa generator weights (`big_lama_generator.safetensors`) with strict key matching.

Config of big-lama: input 4 ch (RGB*(1-mask) + mask), ngf 64, 3 downsamplings, 18 FFC resnet
blocks, ratio_gin = ratio_gout = 0.75 in the blocks, no LFU, reflect padding, sigmoid output.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class FourierUnit(nn.Module):
    def __init__(self, cin: int, cout: int):
        super().__init__()
        self.conv_layer = nn.Conv2d(cin * 2, cout * 2, 1, bias=False)
        self.bn = nn.BatchNorm2d(cout * 2)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        b = x.shape[0]
        f = torch.fft.rfftn(x.float(), dim=(-2, -1), norm="ortho")
        f = torch.stack((f.real, f.imag), dim=-1).permute(0, 1, 4, 2, 3).contiguous()
        f = f.view(b, -1, *f.shape[3:])
        f = self.relu(self.bn(self.conv_layer(f.to(x.dtype))))
        f = f.view(b, -1, 2, *f.shape[2:]).permute(0, 1, 3, 4, 2).contiguous().float()
        f = torch.complex(f[..., 0], f[..., 1])
        return torch.fft.irfftn(f, s=x.shape[-2:], dim=(-2, -1), norm="ortho").to(x.dtype)


class SpectralTransform(nn.Module):
    def __init__(self, cin: int, cout: int, stride: int = 1):
        super().__init__()
        self.downsample = nn.AvgPool2d(2, 2) if stride == 2 else nn.Identity()
        self.conv1 = nn.Sequential(nn.Conv2d(cin, cout // 2, 1, bias=False), nn.BatchNorm2d(cout // 2),
                                   nn.ReLU(inplace=True))
        self.fu = FourierUnit(cout // 2, cout // 2)
        self.conv2 = nn.Conv2d(cout // 2, cout, 1, bias=False)

    def forward(self, x):
        x = self.conv1(self.downsample(x))
        return self.conv2(x + self.fu(x))


class FFC(nn.Module):
    def __init__(self, cin, cout, k, gin, gout, stride=1, padding=0):
        super().__init__()
        in_g = int(cin * gin)
        in_l = cin - in_g
        out_g = int(cout * gout)
        out_l = cout - out_g
        self.gout = gout

        def conv(a, b):
            return nn.Conv2d(a, b, k, stride, padding, bias=False, padding_mode="reflect")
        self.convl2l = conv(in_l, out_l) if in_l and out_l else nn.Identity()
        self.convl2g = conv(in_l, out_g) if in_l and out_g else nn.Identity()
        self.convg2l = conv(in_g, out_l) if in_g and out_l else nn.Identity()
        self.convg2g = SpectralTransform(in_g, out_g, stride) if in_g and out_g else nn.Identity()

    def forward(self, x):
        xl, xg = x if isinstance(x, tuple) else (x, 0)
        ol, og = 0, 0
        if self.gout != 1:
            ol = self.convl2l(xl) + self.convg2l(xg)
        if self.gout != 0:
            og = self.convl2g(xl) + self.convg2g(xg)
        return ol, og


class FFC_BN_ACT(nn.Module):
    def __init__(self, cin, cout, k, gin, gout, stride=1, padding=0):
        super().__init__()
        self.ffc = FFC(cin, cout, k, gin, gout, stride, padding)
        g = int(cout * gout)
        self.bn_l = nn.Identity() if gout == 1 else nn.BatchNorm2d(cout - g)
        self.bn_g = nn.Identity() if gout == 0 else nn.BatchNorm2d(g)
        self.act_l = nn.Identity() if gout == 1 else nn.ReLU(inplace=True)
        self.act_g = nn.Identity() if gout == 0 else nn.ReLU(inplace=True)

    def forward(self, x):
        xl, xg = self.ffc(x)
        return self.act_l(self.bn_l(xl)), self.act_g(self.bn_g(xg))


class FFCResnetBlock(nn.Module):
    def __init__(self, dim, ratio=0.75):
        super().__init__()
        self.conv1 = FFC_BN_ACT(dim, dim, 3, ratio, ratio, padding=1)
        self.conv2 = FFC_BN_ACT(dim, dim, 3, ratio, ratio, padding=1)

    def forward(self, x):
        xl, xg = x if isinstance(x, tuple) else (x, 0)
        yl, yg = self.conv2(self.conv1((xl, xg)))
        return xl + yl, xg + yg


class ConcatTuple(nn.Module):
    def forward(self, x):
        xl, xg = x
        return xl if not torch.is_tensor(xg) else torch.cat(x, dim=1)


class LamaGenerator(nn.Module):
    def __init__(self, ngf=64, n_blocks=18):
        super().__init__()
        m: list[nn.Module] = [nn.ReflectionPad2d(3), FFC_BN_ACT(4, ngf, 7, 0, 0)]
        for i in range(3):
            mult = 2 ** i
            gout = 0.75 if i == 2 else 0
            m.append(FFC_BN_ACT(ngf * mult, ngf * mult * 2, 3, 0, gout, stride=2, padding=1))
        dim = ngf * 8
        m += [FFCResnetBlock(dim) for _ in range(n_blocks)]
        m.append(ConcatTuple())
        for i in range(3):
            mult = 2 ** (3 - i)
            m += [nn.ConvTranspose2d(ngf * mult, ngf * mult // 2, 3, 2, 1, output_padding=1),
                  nn.BatchNorm2d(ngf * mult // 2), nn.ReLU(True)]
        m += [nn.ReflectionPad2d(3), nn.Conv2d(ngf, 3, 7), nn.Sigmoid()]
        self.model = nn.Sequential(*m)

    def forward(self, img, mask):
        """img [B,3,H,W] in [0,1], mask [B,1,H,W] with 1 = unknown. Returns raw prediction."""
        return self.model(torch.cat([img * (1 - mask), mask], dim=1))
