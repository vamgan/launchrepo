import os, sys, tempfile, unittest
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


if __name__ == "__main__":
    unittest.main()
