import sublime

import os
import sys
import imp
import re
from threading import Thread

from .responses import ResponseThreadPool


class RequestCommandMixin:
    """This mixin is the motor responsible for parsing an env, executing requests
    in parallel in the context of this env, invoking activity indicator methods,
    and invoking response handling methods. These methods can be overridden to
    control the behavior of classes that inherit from this mixin.

    It must be mixed in to classes that also inherit from
    `sublime_plugin.TextCommand`.
    """
    REFRESH_MS = 200 # period of checks on async operations, e.g. requests
    ACTIVITY_SPACES = 9 # number of spaces in activity indicator
    MAX_WORKERS = 10 # default request concurrency

    def get_requests(self):
        """This should be overridden to return a list of request strings.
        """
        return []

    def show_activity_for_pending_requests(self, requests, count, activity):
        """Override this method to customize user feedback for pending requests.
        """
        pass

    def handle_response(self, response, num_requests):
        """Override this method to handle a response from a single request. This
        method is called as each response is returned.
        """
        pass

    def handle_responses(self, responses):
        """Override this method to handle responses from all requests executed.
        This method is called after all responses have been returned.
        """
        pass

    def handle_error(self, response, num_requests):
        """Override this method to handle an error from a single request. This
        method is called as each response is returned.
        """
        pass

    def handle_errors(self, responses):
        """Override this method to handle errors from all requests executed. This
        method is called after all responses have been returned.
        """
        errors = ['{}\n{}'.format(r.request, r.error) for r in responses if r.error]
        if errors:
            sublime.error_message('\n\n'.join(errors))

    def run(self, edit):
        self.config = sublime.load_settings('Requester.sublime-settings')
        # `run` runs first, which means `self.config` is available to all methods
        self.reset_env_string()
        self.reset_env_file()
        thread = Thread(target=self._get_env)
        thread.start()
        self._run(thread)

    def _run(self, thread, count=0):
        """Evaluate environment in a separate thread and show an activity
        indicator. Inspect thread at regular intervals until it's finished, at
        which point `make_requests` can be invoked. Return if thread times out.
        """
        REFRESH_MULTIPLIER = 4
        activity = self.get_activity_indicator(count//REFRESH_MULTIPLIER, self.ACTIVITY_SPACES)
        if count > 0: # don't distract user with RequesterEnv status if env can be evaluated quickly
            self.view.set_status('requester.activity', '{} {}'.format( 'RequesterEnv', activity ))

        if thread.is_alive():
            timeout = self.config.get('timeout_env', None)
            if timeout is not None and count * self.REFRESH_MS/REFRESH_MULTIPLIER > timeout * 1000:
                sublime.error_message('Timeout Error: environment took too long to parse')
                self.view.set_status('requester.activity', '')
                return
            sublime.set_timeout(lambda: self._run(thread, count+1), self.REFRESH_MS/REFRESH_MULTIPLIER)

        else:
            requests = self.get_requests()
            self.view.set_status('requester.activity', '')
            self.make_requests(requests, self._env)

    def is_requester_view(self):
        """Was this view opened by a Requester command? This is useful, e.g., to
        avoid resetting `env_file` and `env_string` on these views.
        """
        if self.view.settings().get('requester.response_view', False):
            return True
        if self.view.settings().get('requester.test_view', False):
            return True
        return False

    def reset_env_string(self):
        """(Re)sets the `requester.env_string` setting on the view, if appropriate.
        """
        if self.is_requester_view():
            return

        delimeter = '###env'
        in_block = False
        env_lines = []
        for line in self.view.substr( sublime.Region(0, self.view.size()) ).splitlines():
            if in_block:
                if line == delimeter:
                    in_block = False
                    break
                env_lines.append(line)
            else:
                if line == delimeter:
                    in_block = True
        if not len(env_lines) or in_block: # env block must be closed
            self.view.settings().set('requester.env_string', None)
        self.view.settings().set('requester.env_string', '\n'.join(env_lines))

    def reset_env_file(self):
        """(Re)sets the `requester.env_file` setting on the view, if appropriate.
        """
        if self.is_requester_view():
            return

        scope = {}
        p = re.compile('\s*env_file\s*=.*') # `env_file` can be overridden from within requester file
        for line in self.view.substr( sublime.Region(0, self.view.size()) ).splitlines():
            if p.match(line): # matches only at beginning of string
                try:
                    exec(line, scope) # add `env_file` to `scope` dict
                except:
                    pass
                break # stop looking after first match

        env_file = scope.get('env_file')
        if env_file:
            env_file = str(env_file)
            if os.path.isabs(env_file):
                self.view.settings().set('requester.env_file', env_file)
            else:
                file_path = self.view.file_name()
                if file_path:
                    self.view.settings().set('requester.env_file',
                                             os.path.join(os.path.dirname(file_path), env_file))
        else:
            self.view.settings().set('requester.env_file', None)

    def get_env(self):
        """Computes an env from `requester.env_string` setting, and/or from
        `requester.env_file` setting. Returns an env dictionary.

        http://stackoverflow.com/questions/5362771/load-module-from-string-in-python
        http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
        """
        try:
            del sys.modules['requester.env'] # this avoids a subtle bug, DON'T REMOVE
        except KeyError:
            pass

        env_dict = {}
        env_string = self.view.settings().get('requester.env_string', None)
        if env_string:
            env = imp.new_module('requester.env')
            try:
                exec(env_string, env.__dict__)
            except Exception as e:
                sublime.error_message('EnvBlock Error:\n{}'.format(e))
            else:
                # return a new intance of this dict, or else its values will be reset to `None` after it's returned
                env_dict = dict(env.__dict__)

        env_file = self.view.settings().get('requester.env_file', None)
        if env_file:
            try:
                env = imp.load_source('requester.env', env_file)
            except Exception as e:
                sublime.error_message('EnvFile Error:\n{}'.format(e))
            else:
                env_dict_ = vars(env)
                env_dict.update(env_dict_) # env computed from `env_file` takes precedence
        return env_dict or None

    def _get_env(self):
        """Wrapper calls `get_env` and assigns return value to instance property.
        """
        self._env = self.get_env()

    def make_requests(self, requests, env=None):
        """Make requests concurrently using a `ThreadPool`, which itself runs on
        an alternate thread so as not to block the UI.
        """
        pool = ResponseThreadPool(requests, env, self.MAX_WORKERS) # pass along env vars to thread pool
        sublime.set_timeout_async(lambda: pool.run(), 0) # run on an alternate thread
        sublime.set_timeout(lambda: self.gather_responses(pool), 0)

    def _show_activity_for_pending_requests(self, requests, count):
        """Show activity indicator in status bar.
        """
        activity = self.get_activity_indicator(count, self.ACTIVITY_SPACES)
        self.view.set_status('requester.activity', '{} {}'.format( 'Requester', activity ))
        self.show_activity_for_pending_requests(requests, count, activity)

    def gather_responses(self, pool, count=0, responses=None):
        """Inspect thread pool at regular intervals to remove completed responses
        and handle them, and/or display requests errors.

        Clients can handle responses and errors one at a time as they are
        completed, or as a group when they're all finished. Each response objects
        contains `request`, `response`, `error`, and `ordering` keys.
        """
        self._show_activity_for_pending_requests(pool.pending_requests, count)
        is_done = pool.is_done # cache `is_done` before removing responses from pool

        if responses is None:
            responses = []

        while len(pool.responses): # remove completed responses from thread pool and display them
            r = pool.responses.pop(0)
            responses.append(r)
            self.handle_response(r, num_requests=pool.num_requests())
            self.handle_error(r, num_requests=pool.num_requests())

        if is_done:
            responses.sort(key=lambda response: response.ordering) # parsing order is preserved
            self.handle_responses(responses)
            self.handle_errors(responses)
            self.view.set_status('requester.activity', '') # remove activity indicator from status bar
            return

        sublime.set_timeout(lambda: self.gather_responses(pool, count+1, responses), self.REFRESH_MS)

    @staticmethod
    def get_activity_indicator(count, spaces):
        """Return activity indicator string.
        """
        cycle = count // spaces
        if cycle % 2 == 0:
            before = count % spaces
        else:
            before = spaces - (count % spaces)
        after = spaces - before
        return '[{}={}]'.format(' ' * before, ' ' * after)
