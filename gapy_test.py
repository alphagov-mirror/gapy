from datetime import date
from itertools import islice
import json
import unittest
from oauth2client.clientsecrets import InvalidClientSecretsError

from mock import patch, ANY, Mock, call
from gapy.error import GapyError
from gapy.client import ManagementClient, QueryClient, Client, \
    from_private_key, from_secrets_file, from_credentials_db
from gapy.response import parse_ga_url


def fixture(name):
    return json.load(open("fixtures/%s" % name))


class GapyTest(unittest.TestCase):

    def test_service_account_fails_with_no_private_key(self):
        self.assertRaises(
            GapyError,
            from_private_key,
            "account_name")

    def test_service_account_fails_with_no_storage(self):
        self.assertRaises(
            GapyError,
            from_private_key,
            "account_name", "private_key")

    @patch("gapy.client._build")
    def test_service_account_created(self, build):
        client = from_private_key(
            "account_name", "private_key",
            storage_path="/tmp/foo.dat")
        build.assert_called_with(ANY, ANY, None)
        self.assertTrue(isinstance(client, Client))

    def test_client_from_secrets_file_fails_with_no_secrets_file(self):
        self.assertRaises(
            InvalidClientSecretsError,
            from_secrets_file,
            "/non/existent", storage_path="db")

    def test_client_from_secrets_file_fails_with_no_storage(self):
        self.assertRaises(
            GapyError,
            from_secrets_file,
            "fixtures/example_client_secrets.json")

    @patch('gapy.client._build')
    def test_ga_hook_is_passed_from_private_key(self, build):
        ga_hook = Mock()
        client = from_private_key(
            'account_name', 'private_key',
            storage_path='/tmp/foo.dat',
            ga_hook=ga_hook)

        self.assertEqual(client._ga_hook, ga_hook)


class ManagementClientTest(unittest.TestCase):

    def setUp(self):
        self.service = Mock()
        self.client = ManagementClient(self.service)

    def mock_list(self, name):
        data = fixture("%s.json" % name)
        getattr(self.service.management(),
                name)().list.return_value.execute.return_value = data

    def assert_list_called(self, name, **kwargs):
        getattr(self.service.management(),
                name)().list.assert_called_once_with(**kwargs)

    def test_accounts(self):
        self.mock_list("accounts")

        accounts = self.client.accounts()

        self.assert_list_called("accounts")
        self.assertEqual(accounts.username,
                         "673591833363@developer.gserviceaccount.com")
        self.assertEqual(accounts.kind, "analytics#accounts")

        account = iter(accounts).next()
        self.assertEqual(account["id"], "26179049")

    def test_account(self):
        self.mock_list("accounts")

        account = self.client.account("26179049")

        self.assert_list_called("accounts")
        self.assertEqual(account["id"], "26179049")

    def test_account_fails_with_invalid_account_id(self):
        self.mock_list("accounts")
        self.assertRaises(
            GapyError,
            self.client.account,
            "26179040")

    def test_webproperties(self):
        self.mock_list("webproperties")

        webproperties = self.client.webproperties("26179049")

        self.assert_list_called("webproperties", accountId="26179049")
        self.assertEqual(webproperties.username,
                         "673591833363@developer.gserviceaccount.com")
        self.assertEqual(webproperties.kind, "analytics#webproperties")

        webproperty = iter(webproperties).next()
        self.assertEqual(webproperty["id"], "UA-26179049-1")

    def test_webproperty(self):
        self.mock_list("webproperties")

        webproperty = self.client.webproperty("26179049", "UA-26179049-1")

        self.assert_list_called("webproperties", accountId="26179049")
        self.assertEqual(webproperty["id"], "UA-26179049-1")

    def test_webproperty_fails_with_invalid_id(self):
        self.mock_list("webproperties")
        self.assertRaises(
            GapyError,
            self.client.webproperty,
            "26179049", "UA-26179049-2")

    def test_profiles(self):
        self.mock_list("profiles")

        profiles = self.client.profiles("26179049", "UA-26179049-1")

        self.assert_list_called("profiles", accountId="26179049",
                                webPropertyId="UA-26179049-1")
        self.assertEqual(profiles.username,
                         "673591833363@developer.gserviceaccount.com")
        self.assertEqual(profiles.kind, "analytics#profiles")

    def test_profile(self):
        self.mock_list("profiles")

        profile = self.client.profile("26179049", "UA-26179049-1", "53872948")

        self.assert_list_called("profiles", accountId="26179049",
                                webPropertyId="UA-26179049-1")
        self.assertEqual(profile["id"], "53872948")

    def test_profile_fails_with_invalid_id(self):
        self.mock_list("profiles")
        self.assertRaises(
            GapyError,
            self.client.profile,
            "26179049", "UA-26179049-2", "53872949")

    def test_segments(self):
        self.mock_list("segments")

        segments = self.client.segments()

        self.assert_list_called("segments")
        self.assertEqual(segments.username,
                         "673591833363@developer.gserviceaccount.com")
        self.assertEqual(segments.kind, "analytics#segments")

        segment = iter(segments).next()
        self.assertEqual(segment["id"], "-2")


class QueryClientTest(unittest.TestCase):

    def setUp(self):
        self.service = Mock()
        self.client = QueryClient(self.service)

    def mock_get(self, name, service=None):
        if service is None:
            service = self.service
        data = fixture("%s.json" % name)
        service.data.return_value.ga.return_value.get.return_value. \
            execute.return_value = data

    def assert_get_called(self, **kwargs):
        self.service.data.return_value.ga.return_value.get. \
            assert_called_once_with(**kwargs)

    def get_call_args_list(self):
        return self.service.data.return_value.ga.return_value.get. \
            call_args_list

    def test_short_query(self):
        self.mock_get("short-query")

        results = self.client.get("12345",
                                  date(2012, 1, 1), date(2012, 1, 2),
                                  "metric", "dimension", "dimension2==value")

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric", dimensions="ga:dimension",
            filters="ga:dimension2==value"
        )
        self.assertEqual(results.kind, "analytics#gaData")
        self.assertEqual(len(results), 48)
        result = iter(results).next()
        self.assertEqual(result["metrics"], {"metric": "00"})
        self.assertEqual(result["dimensions"]["dimension"], u'20121110')

    def test_short_query_with_ga_prefixes(self):
        self.mock_get("short-query")

        self.client.get("ga:12345",
                        date(2012, 1, 1), date(2012, 1, 2),
                        "ga:metric", "ga:dimension", "ga:dimension2==value")

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric", dimensions="ga:dimension",
            filters="ga:dimension2==value"
        )

    def test_short_query_with_list_arguments(self):
        self.mock_get("short-query")

        results = self.client.get(
            ["12345", "123456"],
            date(2012, 11, 10), date(2012, 11, 11),
            ["metric", "metric2"], ["dimension", "dimension2"],
            ["dimension3==value", "dimension4==value"]
        )

        self.assert_get_called(
            ids="ga:12345,ga:123456",
            start_date="2012-11-10", end_date="2012-11-11",
            metrics="ga:metric,ga:metric2",
            dimensions="ga:dimension,ga:dimension2",
            filters="ga:dimension3==value,ga:dimension4==value"
        )
        self.assertEqual(results.kind, "analytics#gaData")
        self.assertEqual(len(results), 48)
        result = iter(results).next()
        self.assertEqual(result["metrics"],
                         {"metric": "8083", "metric2": "7643"})
        self.assertEqual(result["dimensions"],
                         {"dimension": "20121110", "dimension2": "00"})
        self.assertEqual(result["start_date"], date(2012, 11, 10))
        self.assertEqual(result["end_date"], date(2012, 11, 11))

    def test_short_query_with_no_dimension_or_filters(self):
        self.mock_get("short-query")

        results = self.client.get("12345",
                                  date(2012, 1, 1), date(2012, 1, 2),
                                  "metric")

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric"
        )
        self.assertEqual(results.kind, "analytics#gaData")
        self.assertEqual(len(results), 48)

    def test_short_query_call_with_max_results(self):
        self.mock_get("short-query")

        # Result is intentionally ignored: short-query doesn't mock length
        # since that wouldn't test any logic in gapy.
        self.client.get("12345", date(2012, 1, 1), date(2012, 1, 2),
                        "metric", max_results=10)

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric",
            max_results=10,
        )

    def test_short_query_call_with_sort(self):
        self.mock_get("short-query")

        # Result is intentionally ignored: short-query doesn't mock length
        # since that wouldn't test any logic in gapy.
        self.client.get("12345", date(2012, 1, 1), date(2012, 1, 2),
                        "metric", sort=["foo", "-bar"])

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric",
            sort="ga:foo,-ga:bar",
        )

    def test_short_query_with_no_rows(self):
        self.mock_get("no-rows")

        results = self.client.get("12345",
                                  date(2012, 1, 1), date(2012, 1, 2),
                                  "metric")

        self.assertEqual(len(results), 0)
        self.assertEqual(len([r for r in results]), 0)

    def test_short_query_call_with_segment(self):
        self.mock_get("short-query")

        # Result is intentionally ignored: short-query doesn't mock length
        # since that wouldn't test any logic in gapy.
        self.client.get("12345", date(2012, 1, 1), date(2012, 1, 2),
                "metric", sort=["foo", "-bar"], segment="gaid::5bSnKB8rR6iYZqYezSS1sQ")

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric",
            sort="ga:foo,-ga:bar",
            segment="gaid::5bSnKB8rR6iYZqYezSS1sQ"
        )

    def test_long_query(self):
        self.mock_get("long-query")

        results = self.client.get("12345",
                                  date(2012, 1, 1), date(2012, 1, 2),
                                  ["metric", "metric2"],
                                  ["dimension", "dimension2"])

        self.assert_get_called(
            ids="ga:12345",
            start_date="2012-01-01", end_date="2012-01-02",
            metrics="ga:metric,ga:metric2",
            dimensions="ga:dimension,ga:dimension2")
        self.assertEqual(results.kind, "analytics#gaData")
        self.assertEqual(len(results), 2)
        i = iter(results)
        i.next()
        i.next()
        i.next()
        i.next()

        calls = self.get_call_args_list()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], call(
            metrics='ga:metric,ga:metric2',
            dimensions='ga:dimension,ga:dimension2',
            ids='ga:12345', end_date='2012-01-02', start_date='2012-01-01',
        ))
        self.assertEqual(calls[1], call(
            metrics='ga:visits,ga:visitors', dimensions='ga:date,ga:hour',
            ids='ga:12345', end_date='2012-01-15', start_date='2012-01-10',
            start_index="1001",
            max_results="1000",  # Because the next-link instructs us to use
                                 # this as max_results.
        ))

    def test_long_query_max_results(self):

        # Check that when max_results is specified and sufficient results
        # are fetched already, nextLink is not followed and the API is called
        # with max_results = N_MAX

        self.mock_get("long-query")

        # This is the number of results
        N_MAX = 2

        results = self.client.get("12345",
                                  date(2012, 1, 1), date(2012, 1, 2),
                                  ["metric", "metric2"],
                                  ["dimension", "dimension2"],
                                  max_results=N_MAX)

        # Fetch a limited number of results
        r = list(islice(results, 0, 99))

        N_ROWS_IN_FIXTURE = 2
        self.assertEqual(len(r), N_ROWS_IN_FIXTURE)

        calls = self.get_call_args_list()

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], call(
            metrics='ga:metric,ga:metric2',
            dimensions='ga:dimension,ga:dimension2',
            ids='ga:12345', end_date='2012-01-02', start_date='2012-01-01',
            max_results=N_MAX,
        ))

    def test_ga_query_hook_is_called(self):
        service = Mock()
        ga_hook = Mock()
        client = QueryClient(service, ga_hook)

        self.mock_get('short-query', service)

        client.get('12345', date(2012, 1, 1), date(2012, 1, 2), 'metric')
        kwargs = {
            'ids': 'ga:12345', 'metrics': 'ga:metric',
            'start_date': '2012-01-01', 'end_date': '2012-01-02',
        }
        ga_hook.assert_called_once_with(kwargs)


class ParseGAUrlTest(unittest.TestCase):

    def test_url_with_semicolon(self):
        next_kwargs = parse_ga_url(
            "https://www.googleapis.com/analytics/v3/data/ga"
            "?ids=ga:53872948"
            "&dimensions=ga:pageTitle,ga:pagePath,ga:day,ga:month,ga:year"
            "&metrics=ga:pageviews"
            "&filters=ga:pagePath!~%5E(/$"
            "%7C/(.*-finished$"
            "%7C%5C?backtoPage"
            "%7Ctransformation"
            "%7Cservice-manual"
            "%7Cperformance"
            "%7Cgovernment"
            "%7Csearch"
            "%7Cdone"
            "%7Cprint).*);"
            "ga:pageTitle!~(404"
            "%7C410"
            "%7C500"
            "%7C504"
            "%7C510"
            "%7CAn+error+has+occurred)"
            "&start-date=2014-02-10"
            "&end-date=2014-02-23"
            "&start-index=1001"
            "&max-results=1000")

        self.assertEqual(
            next_kwargs['filters'],
            "ga:pagePath!~^(/$"
            "|/(.*-finished$"
            "|\\?backtoPage"
            "|transformation"
            "|service-manual"
            "|performance"
            "|government"
            "|search"
            "|done"
            "|print).*);"
            "ga:pageTitle!~("
            "404"
            "|410"
            "|500"
            "|504"
            "|510"
            "|An error has occurred)")


if __name__ == "__main__":
    unittest.main()
