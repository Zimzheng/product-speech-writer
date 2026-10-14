import html
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('renderer', ROOT / 'scripts/render_speaker_html.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RendererTests(unittest.TestCase):
    def test_public_examples_and_determinism(self):
        for name in ('service-review', 'physical-product'):
            with self.subTest(name=name):
                data = json.loads((ROOT / 'examples' / (name + '.json')).read_text())
                output = MODULE.render(data)
                self.assertEqual(output, MODULE.render(data))
                plain = html.unescape(re.sub('<[^>]+>', '', output))
                for chapter in data['chapters']:
                    for block in chapter['blocks']:
                        for paragraph in block['text'].split('\n\n'):
                            self.assertIn(paragraph, plain)

    def test_depth_precedes_next_point_and_transition(self):
        for count in (1, 3, 11):
            chapters = []
            for i in range(count):
                chapters.append({'id': f'c{i}', 'title': 'Topic', 'seconds': 30,
                                 'blocks': [{'id': f'b{i}', 'text': f'Point{i}',
                                             'depth': [{'label': 'Depth', 'text': f'Extra{i}'}]},
                                            {'id': f'n{i}', 'text': f'Next{i}'}],
                                 'transition': f'Bridge{i}'})
            output = MODULE.render({'title': 'Test', 'chapters': chapters})
            self.assertEqual(output.count('class="chapter"'), count)
            self.assertIn(f'seconds>={30 * count}', output)
            for i in range(count):
                self.assertLess(output.index(f'Extra{i}'), output.index(f'Next{i}'))
                self.assertLess(output.index(f'Next{i}'), output.index(f'Bridge{i}'))

    def test_interface_translation_preserves_speech(self):
        text = '\u6838\u5fc3\u5224\u65ad'
        data = {'title': 'Test', 'language': 'en', 'palette': 'monochrome',
                'chapters': [{'id': 'c', 'title': 'Topic', 'seconds': 30,
                              'blocks': [{'id': 'b', 'text': text,
                                          'emphasis': [{'text': text, 'kind': 'key'}]}]}]}
        output = MODULE.render(data)
        self.assertIn('>Speech only</button>', output)
        self.assertIn('>' + text + '</strong>', output)
        self.assertIn("running?'Pause':'Start'", output)

    def test_escaping_and_invalid_emphasis(self):
        output = MODULE.paragraphs('<script>alert("x")</script> &')
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)
        with self.assertRaises(ValueError):
            MODULE.highlighted('abc', [{'text': 'ab', 'kind': 'key'},
                                       {'text': 'bc', 'kind': 'boundary'}])
        with self.assertRaises(ValueError):
            MODULE.highlighted('abc', [{'text': 'missing', 'kind': 'key'}])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.render({'title': 'Test', 'chapters': [{'id': 'same', 'title': 'Topic',
                           'seconds': 30, 'blocks': [{'id': 'same', 'text': 'Point'}]}]})


if __name__ == '__main__':
    unittest.main()
