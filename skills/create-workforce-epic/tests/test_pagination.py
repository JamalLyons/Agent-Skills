"""Complete marker discovery, including large-backlog partial-create recovery."""
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from epiclib import Gh, GhError, parse_epic_marker, render_body, validate_plan  # noqa: E402
from test_epic import FakeGitHub, base_plan, new_epic_plan, run_apply  # noqa: E402


class PagedGh(Gh):
    def __init__(self, items):
        self.items = items
        self.requests = []

    def rest(self, method, path, body=None):
        self.requests.append(path)
        query = parse_qs(urlsplit(path).query)
        page, size = int(query['page'][0]), int(query['per_page'][0])
        return self.items[(page - 1) * size:page * size]


class PaginationTests(unittest.TestCase):
    def test_default_reads_beyond_one_thousand(self):
        items = [{'number': i} for i in range(1051)]
        gh = PagedGh(items)
        self.assertEqual(gh.paginate('repos/acme/app/issues?state=all'), items)
        self.assertEqual(len(gh.requests), 11)
        self.assertIn('state=all&per_page=100&page=11', gh.requests[-1])

    def test_exact_full_page_needs_exhaustion_request(self):
        gh = PagedGh(list(range(1000)))
        self.assertEqual(len(gh.paginate('issues', limit=1000)), 1000)
        self.assertEqual(len(gh.requests), 11)

    def test_explicit_limit_fails_without_returning_partial_discovery(self):
        gh = PagedGh(list(range(1001)))
        with self.assertRaisesRegex(GhError, 'discovery incomplete.*limit 1000 exceeded'):
            gh.paginate('issues', limit=1000)

    def test_invalid_limit_is_rejected_before_a_request(self):
        gh = PagedGh([])
        for bound in (0, -1, True, 1.5, '100'):
            with self.subTest(limit=bound), self.assertRaises(ValueError):
                gh.paginate('issues', limit=bound)
        self.assertEqual(gh.requests, [])

    def test_malformed_page_does_not_return_earlier_pages(self):
        class MalformedGh(PagedGh):
            def rest(self, method, path, body=None):
                if 'page=2' in path:
                    return {'message': 'unexpected response'}
                return super().rest(method, path, body)

        with self.assertRaisesRegex(GhError, 'expected a list'):
            MalformedGh(list(range(100))).paginate('issues')

    def test_failure_on_later_page_propagates(self):
        class FailingGh(PagedGh):
            def rest(self, method, path, body=None):
                if 'page=2' in path:
                    raise GhError(None, 'connection reset')
                return super().rest(method, path, body)

        with self.assertRaisesRegex(GhError, 'connection reset'):
            FailingGh(list(range(100))).paginate('issues')


class LargeBacklogRecoveryTests(unittest.TestCase):
    def github_with_backlog(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        for i in range(1000):
            gh.add_issue(f'Historical task {i}', 'unrelated', labels=['workforce'], state='closed')
        return gh

    def test_lost_epic_create_response_is_recovered_beyond_old_cap(self):
        gh = self.github_with_backlog()
        gh.fail_on = ('POST', r'/issues$', 1, 'after')
        code, _, _ = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 1)
        roots = [i for i in gh.issues.values() if parse_epic_marker(i['body'])]
        self.assertEqual(len(roots), 1)

        code, report, err = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 0, err)
        self.assertEqual(report['epic'], roots[0]['number'])
        self.assertFalse(report['epic_created'])
        self.assertEqual(sum(bool(parse_epic_marker(i['body'])) for i in gh.issues.values()), 1)

    def test_unlinked_task_beyond_old_cap_is_reused(self):
        gh = self.github_with_backlog()
        plan = validate_plan(base_plan())
        existing = gh.add_issue('Add API', render_body(plan, plan.by_key['T1'], {}), labels=['workforce'])
        code, report, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0, err)
        self.assertEqual(report['tasks']['T1'], existing['number'])
        self.assertEqual(sum(i['title'] == 'Add API' for i in gh.issues.values()), 1)


if __name__ == '__main__':
    unittest.main()
