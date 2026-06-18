from leet2local.html_parser import html_to_markdown


def test_basic_conversion():
    html = "<p>Given an array <code>nums</code>, return the answer.</p>"
    md = html_to_markdown(html)
    assert "nums" in md
    assert "<p>" not in md


def test_pre_block():
    html = "<pre><strong>Input:</strong> nums = [1,2], target = 9\n<strong>Output:</strong> [0,1]</pre>"
    md = html_to_markdown(html)
    assert "Input" in md
    assert "[0,1]" in md


def test_sup_conversion():
    html = "<p>10<sup>9</sup></p>"
    md = html_to_markdown(html)
    assert "^9" in md


def test_empty_html():
    assert html_to_markdown("") == ""


def test_no_triple_blank_lines():
    html = "<p>A</p>\n\n\n\n<p>B</p>"
    md = html_to_markdown(html)
    assert "\n\n\n" not in md
