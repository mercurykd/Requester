import sublime, sublime_plugin

import webbrowser


class RequesterReplaceViewTextCommand(sublime_plugin.TextCommand):
    """`TextCommand` to replace all text in view, without highlighting text after.
    Optionally leave cursor at `point`.
    """
    def run(self, edit, text, point=None):
        self.view.erase(
            edit, sublime.Region(0, self.view.size())
        )
        self.view.insert(edit, 0, text)
        if point:
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(point))


class RequesterCloseResponseTabsCommand(sublime_plugin.WindowCommand):
    """`TextCommand` to replace all text in view, without highlighting text after.
    Optionally leave cursor at `point`.
    """
    def run(self):
        for sheet in self.window.sheets():
            view = sheet.view()
            if view and view.settings().get('requester.response_view', False):
                view.close()


class RequesterShowTutorialCommand(sublime_plugin.WindowCommand):
    """Show a modified, read-only version of README that can be used to see how
    Requester works.
    """
    def run(self):
        tutorial_content = sublime.load_resource('Packages/Requester/docs/tutorial.md')
        env_content = sublime.load_resource('Packages/Requester/docs/requester_env.py')

        view = self.window.new_file()
        view.run_command('requester_replace_view_text', {'text': tutorial_content, 'point': 0})
        view.settings().set('requester.env', env_content)
        view.set_read_only(True)
        view.set_scratch(True)
        view.set_syntax_file('Packages/MarkdownEditing/Markdown.tmLanguage')
        # this doesn't raise an exception if it fails
        view.set_name('Requester Tutorial')


class RequesterShowSyntaxCommand(sublime_plugin.WindowCommand):
    """Show a modified, read-only version of README that can be used to see how
    Requester works.
    """
    def run(self):
        webbrowser.open_new_tab('http://docs.python-requests.org/en/master/user/quickstart/')