import os, struct, sys, tempfile, unittest
from unittest import mock
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import render

PROFILE = {"facts": {"name": {"value": "declutter", "source": "git remote"},
                     "license": {"value": "MIT", "source": "LICENSE"}},
           "unavailable": {"tagline": "not declared"}}


class TestFill(unittest.TestCase):
    def test_replaces_one_placeholder(self):
        self.assertEqual(render.fill("hello {{name}}", PROFILE, {}), "hello declutter")

    def test_replaces_several_placeholders(self):
        self.assertEqual(
            render.fill("{{name}} is {{license}}", PROFILE, {}),
            "declutter is MIT",
        )

    def test_extras_override_facts(self):
        self.assertEqual(
            render.fill("{{name}}", PROFILE, {"name": "override"}),
            "override",
        )

    def test_unknown_key_raises_and_names_it(self):
        with self.assertRaises(SystemExit) as ctx:
            render.fill("{{nope}}", PROFILE, {})
        self.assertIn("nope", str(ctx.exception))

    def test_unavailable_key_raises_with_reason(self):
        with self.assertRaises(SystemExit) as ctx:
            render.fill("{{tagline}}", PROFILE, {})
        message = str(ctx.exception)
        self.assertIn("tagline", message)
        self.assertIn("not declared", message)

    def test_html_special_characters_are_escaped(self):
        extras = {"tagline": "<script>&\"'"}
        result = render.fill("{{tagline}}", PROFILE, extras)
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_text_with_no_placeholders_is_unchanged(self):
        self.assertEqual(render.fill("plain text", PROFILE, {}), "plain text")


class TestFindChrome(unittest.TestCase):
    def test_honours_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "my-chrome")
            with open(fake, "w") as fh:
                fh.write("#!/bin/sh\n")
            os.chmod(fake, 0o755)
            self.assertEqual(render.find_chrome(explicit=fake), fake)

    def test_honours_chrome_env_var(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "env-chrome")
            with open(fake, "w") as fh:
                fh.write("#!/bin/sh\n")
            os.chmod(fake, 0o755)
            old = os.environ.get("CHROME")
            os.environ["CHROME"] = fake
            try:
                self.assertEqual(render.find_chrome(), fake)
            finally:
                if old is None:
                    os.environ.pop("CHROME", None)
                else:
                    os.environ["CHROME"] = old

    def test_returns_none_when_nothing_found(self):
        old = os.environ.pop("CHROME", None)
        try:
            self.assertIsNone(render.find_chrome(candidates=[]))
        finally:
            if old is not None:
                os.environ["CHROME"] = old


class TestRender(unittest.TestCase):
    def _write_template(self, tmp, html_text):
        path = os.path.join(tmp, "template.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html_text)
        return path

    def test_missing_chrome_returns_ok_false_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write_template(tmp, "<html><body>{{name}}</body></html>")
            out_path = os.path.join(tmp, "out.png")
            with mock.patch("render.find_chrome", return_value=None):
                result = render.render(template, PROFILE, out_path, 100, 50)
            self.assertFalse(result.ok)
            self.assertIn("chrome", result.reason.lower())

    def test_unprovable_placeholder_raises_before_chrome_launches(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write_template(tmp, "<html><body>{{tagline}}</body></html>")
            out_path = os.path.join(tmp, "out.png")
            with mock.patch("render.find_chrome") as find_chrome_mock:
                with self.assertRaises(SystemExit):
                    render.render(template, PROFILE, out_path, 100, 50)
                find_chrome_mock.assert_not_called()

    @unittest.skipIf(render.find_chrome() is None, "no Chrome on this machine")
    def test_produces_a_real_png_with_scaled_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write_template(
                tmp, "<html><body style='margin:0'>{{name}}</body></html>"
            )
            out_path = os.path.join(tmp, "out.png")
            result = render.render(template, PROFILE, out_path, 100, 50, scale=2)
            self.assertTrue(result.ok, result.reason)
            self.assertEqual(result.path, out_path)
            with open(out_path, "rb") as fh:
                header = fh.read(24)
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", header[16:24])
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)


if __name__ == "__main__":
    unittest.main()
