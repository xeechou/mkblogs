#!/usr/bin/env python
# coding: utf-8

import os
import shutil
import tempfile
import unittest

from mkdocs import build, nav, config
from mkdocs.compat import zip
from mkdocs.exceptions import MarkdownNotFound
from mkdocs.tests.base import dedent


class BuildTests(unittest.TestCase):

    def test_empty_document(self):
        html, toc, meta = build.convert_markdown("")

        self.assertEqual(html, '')
        self.assertEqual(len(list(toc)), 0)
        self.assertEqual(meta, {})

    def test_convert_markdown(self):
        """
        Ensure that basic Markdown -> HTML and TOC works.
        """

        html, toc, meta = build.convert_markdown(dedent("""
            page_title: custom title

            # Heading 1

            This is some text.

            # Heading 2

            And some more text.
        """))

        expected_html = dedent("""
            <h1 id="heading-1">Heading 1</h1>
            <p>This is some text.</p>
            <h1 id="heading-2">Heading 2</h1>
            <p>And some more text.</p>
        """)

        expected_toc = dedent("""
            Heading 1 - #heading-1
            Heading 2 - #heading-2
        """)

        expected_meta = {'page_title': ['custom title']}

        self.assertEqual(html.strip(), expected_html)
        self.assertEqual(str(toc).strip(), expected_toc)
        self.assertEqual(meta, expected_meta)

    def test_convert_internal_link(self):
        md_text = 'An [internal link](internal.md) to another document.'
        expected = '<p>An <a href="internal/">internal link</a> to another document.</p>'
        html, toc, meta = build.convert_markdown(md_text)
        self.assertEqual(html.strip(), expected.strip())

    def test_convert_multiple_internal_links(self):
        md_text = '[First link](first.md) [second link](second.md).'
        expected = '<p><a href="first/">First link</a> <a href="second/">second link</a>.</p>'
        html, toc, meta = build.convert_markdown(md_text)
        self.assertEqual(html.strip(), expected.strip())

    def test_convert_internal_link_differing_directory(self):
        md_text = 'An [internal link](../internal.md) to another document.'
        expected = '<p>An <a href="../internal/">internal link</a> to another document.</p>'
        html, toc, meta = build.convert_markdown(md_text)
        self.assertEqual(html.strip(), expected.strip())

    def test_convert_internal_link_with_anchor(self):
        md_text = 'An [internal link](internal.md#section1.1) to another document.'
        expected = '<p>An <a href="internal/#section1.1">internal link</a> to another document.</p>'
        html, toc, meta = build.convert_markdown(md_text)
        self.assertEqual(html.strip(), expected.strip())

    def test_convert_internal_media(self):
        """Test relative image URL's are the same for different base_urls"""
        pages = [
            ('index.md',),
            ('internal.md',),
            ('sub/internal.md')
        ]

        site_navigation = nav.SiteNavigation(pages)

        expected_results = (
            './img/initial-layout.png',
            '../img/initial-layout.png',
            '../img/initial-layout.png',
        )

        template = '<p><img alt="The initial MkDocs layout" src="%s" /></p>'

        for (page, expected) in zip(site_navigation.walk_pages(), expected_results):
            md_text = '![The initial MkDocs layout](img/initial-layout.png)'
            html, _, _ = build.convert_markdown(md_text, site_navigation=site_navigation)
            self.assertEqual(html, template % expected)

    def test_convert_internal_asbolute_media(self):
        """Test absolute image URL's are correct for different base_urls"""
        pages = [
            ('index.md',),
            ('internal.md',),
            ('sub/internal.md')
        ]

        site_navigation = nav.SiteNavigation(pages)

        expected_results = (
            './img/initial-layout.png',
            '../img/initial-layout.png',
            '../../img/initial-layout.png',
        )

        template = '<p><img alt="The initial MkDocs layout" src="%s" /></p>'

        for (page, expected) in zip(site_navigation.walk_pages(), expected_results):
            md_text = '![The initial MkDocs layout](/img/initial-layout.png)'
            html, _, _ = build.convert_markdown(md_text, site_navigation=site_navigation)
            self.assertEqual(html, template % expected)

    def test_dont_convert_code_block_urls(self):
        pages = [
            ('index.md',),
            ('internal.md',),
            ('sub/internal.md')
        ]

        site_navigation = nav.SiteNavigation(pages)

        expected = dedent("""
        <p>An HTML Anchor::</p>
        <pre><code>&lt;a href="index.md"&gt;My example link&lt;/a&gt;
        </code></pre>
        """)

        for page in site_navigation.walk_pages():
            markdown = 'An HTML Anchor::\n\n    <a href="index.md">My example link</a>\n'
            html, _, _ = build.convert_markdown(markdown, site_navigation=site_navigation)
            self.assertEqual(dedent(html), expected)

    def test_anchor_only_link(self):

        pages = [
            ('index.md',),
            ('internal.md',),
            ('sub/internal.md')
        ]

        site_navigation = nav.SiteNavigation(pages)

        for page in site_navigation.walk_pages():
            markdown = '[test](#test)'
            html, _, _ = build.convert_markdown(markdown, site_navigation=site_navigation)
            self.assertEqual(html, '<p><a href="#test">test</a></p>')

    def test_ignore_external_link(self):
        md_text = 'An [external link](http://example.com/external.md).'
        expected = '<p>An <a href="http://example.com/external.md">external link</a>.</p>'
        html, toc, meta = build.convert_markdown(md_text)
        self.assertEqual(html.strip(), expected.strip())

    def test_not_use_directory_urls(self):
        md_text = 'An [internal link](internal.md) to another document.'
        expected = '<p>An <a href="internal/index.html">internal link</a> to another document.</p>'
        pages = [
            ('internal.md',)
        ]
        site_navigation = nav.SiteNavigation(pages, use_directory_urls=False)
        html, toc, meta = build.convert_markdown(md_text, site_navigation=site_navigation)
        self.assertEqual(html.strip(), expected.strip())

    def test_markdown_table_extension(self):
        """
        Ensure that the table extension is supported.
        """

        html, toc, meta = build.convert_markdown(dedent("""
        First Header   | Second Header
        -------------- | --------------
        Content Cell 1 | Content Cell 2
        Content Cell 3 | Content Cell 4
        """))

        expected_html = dedent("""
        <table>
        <thead>
        <tr>
        <th>First Header</th>
        <th>Second Header</th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td>Content Cell 1</td>
        <td>Content Cell 2</td>
        </tr>
        <tr>
        <td>Content Cell 3</td>
        <td>Content Cell 4</td>
        </tr>
        </tbody>
        </table>
        """)

        self.assertEqual(html.strip(), expected_html)

    def test_markdown_fenced_code_extension(self):
        """
        Ensure that the fenced code extension is supported.
        """

        html, toc, meta = build.convert_markdown(dedent("""
        ```
        print 'foo'
        ```
        """))

        expected_html = dedent("""
        <pre><code>print 'foo'\n</code></pre>
        """)

        self.assertEqual(html.strip(), expected_html)

    def test_markdown_custom_extension(self):
        """
        Check that an extension applies when requested in the arguments to
        `convert_markdown`.
        """
        md_input = "foo__bar__baz"

        # Check that the plugin is not active when not requested.
        expected_without_smartstrong = "<p>foo<strong>bar</strong>baz</p>"
        html_base, _, _ = build.convert_markdown(md_input)
        self.assertEqual(html_base.strip(), expected_without_smartstrong)

        # Check that the plugin is active when requested.
        expected_with_smartstrong = "<p>foo__bar__baz</p>"
        html_ext, _, _ = build.convert_markdown(md_input, extensions=['smart_strong'])
        self.assertEqual(html_ext.strip(), expected_with_smartstrong)

    def test_markdown_duplicate_custom_extension(self):
        """
        Duplicated extension names should not cause problems.
        """
        md_input = "foo"
        html_ext, _, _ = build.convert_markdown(md_input, ['toc'])
        self.assertEqual(html_ext.strip(), '<p>foo</p>')

    def test_copying_media(self):

        docs_dir = tempfile.mkdtemp()
        site_dir = tempfile.mkdtemp()
        try:
            # Create a non-empty markdown file, image, dot file and dot directory.
            f = open(os.path.join(docs_dir, 'index.md'), 'w')
            f.write(dedent("""
                page_title: custom title

                # Heading 1

                This is some text.

                # Heading 2

                And some more text.
            """))
            f.close()
            open(os.path.join(docs_dir, 'img.jpg'), 'w').close()
            open(os.path.join(docs_dir, '.hidden'), 'w').close()
            os.mkdir(os.path.join(docs_dir, '.git'))
            open(os.path.join(docs_dir, '.git/hidden'), 'w').close()

            conf = config.validate_config({
                'site_name': 'Example',
                'docs_dir': docs_dir,
                'site_dir': site_dir
            })
            build.build(conf)

            # Verify only the markdown (coverted to html) and the image are copied.
            self.assertTrue(os.path.isfile(os.path.join(site_dir, 'index.html')))
            self.assertTrue(os.path.isfile(os.path.join(site_dir, 'img.jpg')))
            self.assertFalse(os.path.isfile(os.path.join(site_dir, '.hidden')))
            self.assertFalse(os.path.isfile(os.path.join(site_dir, '.git/hidden')))
        finally:
            shutil.rmtree(docs_dir)
            shutil.rmtree(site_dir)

    def test_strict_mode_valid(self):
        pages = [
            ('index.md',),
            ('internal.md',),
            ('sub/internal.md')
        ]
        site_nav = nav.SiteNavigation(pages)

        valid = "[test](internal.md)"
        build.convert_markdown(valid, site_nav, strict=False)
        build.convert_markdown(valid, site_nav, strict=True)

    def test_strict_mode_invalid(self):
        pages = [
            ('index.md',),
            ('internal.md',),
            ('sub/internal.md')
        ]
        site_nav = nav.SiteNavigation(pages)

        invalid = "[test](bad_link.md)"
        build.convert_markdown(invalid, site_nav, strict=False)

        self.assertRaises(
            MarkdownNotFound,
            build.convert_markdown, invalid, site_nav, strict=True)
