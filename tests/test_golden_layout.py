import ast
from pathlib import Path
import tempfile
import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text
from pypdf import PdfReader

ENGINE = Path(__file__).resolve().parents[1] / 'assets/bend-pdf-golden-001-visual/engine_u_endplates.py'


class GoldenLayout(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(ENGINE.read_text())
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        self.ns = dict(FancyBboxPatch=FancyBboxPatch, Text=Text, MINPT=9.4,
                       FS_BOX=9.4, FS_NOTE=9.4, NAVY='navy', REDC='red', DIMC='blue', PW=420, PH=297)
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(ENGINE), 'exec'), self.ns)
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.ax.set(xlim=(0, 420), ylim=(0, 297))
        self.ax.axis('off')

    def tearDown(self):
        plt.close(self.fig)

    def test_long_hole_text_wraps_inside_box_without_losing_characters(self):
        line = 'P1 diameter16.5@(28.5,134.25)/P2 diameter16.5@(28.5,170.75)' * 2
        self.ns['box'](self.ax, 20, 20, 100, 180, [line])
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        right = self.ax.transData.transform((117, 20))[0]
        text = ''.join(t.get_text().replace('\n', '') for t in self.ax.texts)
        self.assertEqual(text, line)
        self.assertTrue(all(t.get_window_extent(renderer).x1 <= right + 1 for t in self.ax.texts))

    def test_box_overflow_is_rejected_instead_of_dropping_notes(self):
        with self.assertRaisesRegex(ValueError, 'PDF_LAYOUT'):
            self.ns['box'](self.ax, 20, 20, 40, 10, ['many notes ' * 50])

    def test_customer_words_paginate_without_losing_or_overlapping_text(self):
        self.assertIn('customer_requirement_pages', self.ns)
        self.fig.set_size_inches(420/25.4, 297/25.4)
        self.ax.set_position([0, 0, 1, 1])
        original = 'Original: 20.5cm x 19.5cm; hole at 32mm.\n' * 45 + 'Unbroken' * 250
        pages = self.ns['customer_requirement_pages'](self.ax, {
            'customer_requirement_text': original,
            'customer_requirement_updates': ['Correction: hole center at 320mm.']})
        self.assertGreater(len(pages), 1)
        joined = ''.join(text for page in pages for text, color in page)
        self.assertIn(original.replace('\n', ''), joined)
        self.assertIn('Correction: hole center at 320mm.', joined)
        for rows in pages:
            self.ax.clear(); self.ax.set(xlim=(0, 420), ylim=(0, 297)); self.ax.axis('off')
            self.ns['box'](self.ax, 12, 26, 396, 222, rows, title='Customer requirements')
            self.assertEqual(self.ns['layout_issues'](self.fig), [])

    def test_customer_dollar_signs_are_printed_as_original_text(self):
        self.ns['box'](self.ax, 20, 20, 300, 100, ['$12_5$ & <tag>'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'plain.pdf'
            self.fig.savefig(path)
            self.assertIn('$12_5$ & <tag>', PdfReader(path).pages[0].extract_text())

    def test_page_check_catches_cross_axes_overlap_and_clipping(self):
        self.assertIn('layout_issues', self.ns, 'page-wide text gate missing')
        self.ax.text(200, 100, 'first')
        other = self.fig.add_axes(self.ax.get_position())
        other.set(xlim=(0, 420), ylim=(0, 297)); other.axis('off')
        other.text(200, 100, 'second')
        self.fig.text(1.01, .5, 'outside')
        issues = self.ns['layout_issues'](self.fig)
        self.assertTrue(any(i['kind'] == 'overlap' for i in issues))
        self.assertTrue(any(i['kind'] == 'outside_page' for i in issues))

    def test_panel_handle_caption_uses_actual_rotated_hole_rows(self):
        self.assertIn('panel_handle_row_note', self.ns)
        holes = [dict(point=[0, y, z]) for y, z in
                 [(122.5, 144.4), (207.5, 144.4), (134, 114.4), (196, 114.4)]]
        self.assertEqual(self.ns['panel_handle_row_note'](holes),
                         '宽排85 Z144.4在上；窄排62 Z114.4在下')
        for h in holes:
            h['point'][2] = round(258.8-h['point'][2], 5)
        self.assertEqual(self.ns['panel_handle_row_note'](holes),
                         '宽排85 Z114.4在下；窄排62 Z144.4在上')


if __name__ == '__main__':
    unittest.main()
