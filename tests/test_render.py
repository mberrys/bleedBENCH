"""render_rect: box -> render-space mapping on a page whose MediaBox does not start at (0, 0)."""
import pymupdf

from bleedbench.render.pdf_render import _prepare, render_rect


def _offset_pdf() -> bytes:
    """Letter page whose media sits at (20, 10) in PDF space, with a crop inside it."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    doc.xref_set_key(page.xref, "MediaBox", "[20 10 632 802]")
    doc.xref_set_key(page.xref, "CropBox", "[40 30 612 782]")
    doc.xref_set_key(page.xref, "TrimBox", "[50 40 592 772]")
    doc.xref_set_key(page.xref, "BleedBox", "[41 31 601 781]")
    blob = doc.tobytes()
    doc.close()
    return blob


def test_render_rect_maps_offset_boxes_to_render_space():
    doc = pymupdf.open(stream=_offset_pdf(), filetype="pdf")
    page = _prepare(doc, 0)
    # _prepare forces CropBox := MediaBox, so render space starts at the media origin (20, 10)
    assert doc.xref_get_key(page.xref, "CropBox") == doc.xref_get_key(page.xref, "MediaBox")
    assert (page.rect.x0, page.rect.y0) == (0.0, 0.0) and page.rect.width == 612
    # raw boxes are reported against the media origin; render space is against the CropBox origin
    assert (page.trimbox.x0, page.trimbox.y0) == (50.0, 30.0)
    tb = render_rect(page, page.trimbox)
    assert (tb.x0, tb.y0, tb.x1, tb.y1) == (30.0, 30.0, 572.0, 762.0)
    bb = render_rect(page, page.bleedbox)
    assert (bb.x0, bb.y0, bb.x1, bb.y1) == (21.0, 21.0, 581.0, 771.0)
    # the bleed ring is 9 pt on every side of the trim, in render space too
    assert (tb.x0 - bb.x0, tb.y0 - bb.y0, bb.x1 - tb.x1, bb.y1 - tb.y1) == (9.0, 9.0, 9.0, 9.0)
    doc.close()
