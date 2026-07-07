# Agents

Detailed guidance for AI agents working on this codebase.

## Policy

- No unicode. All files must be ASCII-only.

## Reference

- [General coding guidelines](agents/guidelines.md)

## Tests

Comprehensive privleap tests -- wire-protocol parser and authorizer fuzzers
(incl. coverage-guided Atheris and session-state fuzzers) and live-daemon
end-to-end suites -- are too high-volume for human review and live in the
AI-maintained dist-ai repo, not here:

  https://github.com/org-ai-assisted/dist-ai -> usr/share/privleap-tests/

Run them against this checkout:

    PRIVLEAP_REPO="$PWD" privleap-tests        # parser/authorizer property + fuzz
    PRIVLEAP_REPO="$PWD" privleap-tests-e2e    # live daemon over a socket (needs setup)
