# Contributing
Please do! Possible improvements:

- Snippets and examples for more auth schemes
  + Requester can import __any Python package__
    * OAuth 2, using `requests-oauthlib`
    * Other common auth protocols, using whichever package is best
  + `RequesterAuthOptionsCommand` for snippets
  + Examples in documentation
- More export/import formats
  + [HTTP](https://tools.ietf.org/html/rfc7230)
- Randomized requests with benchmark runs (e.g. for fuzz testing)
  + Execute all requests constructred from an iterable?
- Improved support for GraphQL
  + A clone of GraphiQL?
  + __Documentation Explorer__ and __Autocomplete__
  + https://github.com/tryolabs/graphql-parser
  + This is a really big undertaking
- Improve architecture and test coverage
  + More pure functions, fewer coupling points to Sublime Text API
  + Test coverage for syntax files
- Tell your friends about Requester!


## How Does It Work?
The core API is defined in modules under the `core` directory. The main class is `RequestCommandMixin`.

This mixin is the motor for parsing an env, executing requests in parallel in the context of this env, invoking activity indicator methods, and invoking response handling methods. These methods can be overridden to control the behavior of classes that inherit from this mixin.

The mixin uses the `ResponseThreadPool` class, which wraps a thread pool to execute requests in parallel. Default concurrency is determined by the mixin's `MAX_WORKERS` class property. The thread pool is inspected at regular intervals to remove completed responses and handle them, and show activity for pending requests.

Command classes that use this mixin can override `handle_response` and/or `handle_responses`. This way they can handle responses one at a time as they are completed, or as a group when they're all finished. Each response object contains a `req` namedtuple with a bunch of useful properties, the `res` (a __requests.Response__ object), and an `err` string. Responses are sorted by request parsing order.


### Parser
Command classes __must__ also override `get_requests`, which must return a list of request strings, for example strings parsed from the current view. To simplify this, `core` has a `parsers` module. The important parser is `parse_requests`. It takes a string, such as a selection from a view, and returns a list of all calls to `requests` in the string.


### Use of Eval and Exec
`exec` is used to build an environment dict from a string, in basically the same way `import` populates a variables dict from a module. The `exec`ed string is simply the concatenation of the env block and the env file.

`eval` is used in `prepare_request`, in conjunction with `parse_args`, to parse the args passed to `requests.<method>`. This way Requester can modify, remove, or add to these args before actually calling `requests.<method>`. Much of Requester's most powerful behavior derives from this ability.


### Writing a New Command Class
If you want to write a new command class for Requester, check out how `RequesterCommand` works; it simply uses the mixin and overrides `get_requests` and `handle_response`.

If you want a better understanding of the details, dive into `core` directory. This is where the heavy lifting is done.


## Installing the `pre-commit` Git hook
Run `cd .git/hooks && ln -s -f ../../docs/_hooks/* ./` from the root of the repo. This creates a symlink from the `.git/hooks` directory to Requester's `pre-commit` hook. This hook runs code linting and style checking with `flake8`, and builds the documentation from the sources in `docs/_content`.


## Python Linting and Code Style
Uses __flake8__. First, install __flake8__ with `pip3 install flake8`.

As long as you installed Requester's `pre-commit` hook (see above), you will be unable to commit anything that doesn't pass __flake8__ validation.

All classes and methods should have docstrings, limited to 82 characters per line. Except for `run` and `__init__`. Feel free to add comments for anything that's not obvious.


## Tests
Tests are divided into tests of the `core` package, which depend on a mocked `sublime` and run on Travis, and integration tests run within Sublime Text.

Many tests for Requester are asynchronous, because they depend on responses coming back before examining response tabs. For this reason, tests are executed against a local server powered by __httpbin__. You can install __httpbin__ by running `pip install httpbin`. You can then run it with `gunicorn httpbin:app` or `gunicorn --access-logfile /dev/stdout httpbin:app`.

To run `core` tests, execute `python -m unittest tests.core -v` from the root of the repo. 

To run the integration tests, install __UnitTesting__ via Package Control. Read more about [UnitTesting](https://github.com/randy3k/UnitTesting-example). Also, make sure you've cloned the Requester repo into your __Packages__ directory.

Run integration tests before committing changes. Look for __UnitTesting__ in the command palette, hit enter, and type `Requester`. Or, if you've created a project for Requester, run __UnitTesting: Test Current Project__.


## Docs
`README.md` is generated by Requester's `pre-commit` hook. If you want to improve the docs, __don't edit README.md__. The correct file is `docs/_content/body.md`.