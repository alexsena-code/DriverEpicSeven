"""Explicit test tiers and optional measurements; default pytest still runs all."""
import pytest
import json
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption('--test-profile',metavar='JSON',help='Write opt-in timing/native counters to this private report')
    parser.addoption('--fixture-cache',choices=('session','off'),default='session',help='Offline exact-input cache; default session, off for independent replay')
    parser.addoption('--test-tier',choices=('all','fast','native'),default='all',help='Explicit audited test selection; default all')
    parser.addoption('--test-audit',metavar='JSON',help='Write test/fixture dependency classification')


def pytest_configure(config):
    if config.getoption('--test-profile'):
        from native_profile import NativeProfile
        config._native_profile=NativeProfile(config.getoption('--test-profile'))
        config._native_profile.install()
    if config.getoption('--fixture-cache')=='session' and config.getoption('--test-tier')!='fast':
        from fixture_cache import FixtureCache
        config._fixture_cache=FixtureCache();config._fixture_cache.install()


def pytest_collection_modifyitems(config,items):
    from native_tiers import classify
    audit=[];selected=[];deselected=[];tier=config.getoption('--test-tier')
    for item in items:
        reasons=classify(item);native=bool(reasons)
        item.add_marker(pytest.mark.native if native else pytest.mark.fast)
        audit.append({'nodeid':item.nodeid,'tier':'native' if native else 'fast','reasons':reasons,
                      'fixtures':item.fixturenames,'private_fixtures_marker':bool(item.get_closest_marker('fixtures'))})
        (selected if tier=='all' or (tier=='native')==native else deselected).append(item)
    if deselected:config.hook.pytest_deselected(items=deselected);items[:]=selected
    output=config.getoption('--test-audit')
    if output:
        path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(audit,indent=2),encoding='utf-8')


@pytest.fixture(autouse=True)
def _fast_native_guard(request,monkeypatch):
    """Make a missed native dependency fail the fast tier, never run silently."""
    if request.config.getoption('--test-tier')=='fast':
        from maa.resource import Resource
        from maa.tasker import Tasker
        from maa.controller import CustomController,Win32Controller
        def forbidden(*args,**kwargs):
            raise AssertionError('Native dependency missing from test-tier audit.')
        for owner in (Resource,Tasker,CustomController,Win32Controller):
            monkeypatch.setattr(owner,'__init__',forbidden)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    profile=getattr(item.config,'_native_profile',None)
    if profile:profile.current=item.nodeid;profile.phase='setup'
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    profile=getattr(item.config,'_native_profile',None)
    if profile:profile.current=item.nodeid;profile.phase='call'
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
    profile=getattr(item.config,'_native_profile',None)
    if profile:profile.current=item.nodeid;profile.phase='teardown'
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield
    profile=getattr(item.config,'_native_profile',None)
    if profile:
        report=outcome.get_result()
        profile.reports[item.nodeid][report.when]={'seconds':report.duration,'outcome':report.outcome,
                                                'wasxfail':getattr(report,'wasxfail',None)}


def pytest_sessionfinish(session,exitstatus):
    cache=getattr(session.config,'_fixture_cache',None)
    if cache:cache.close()
    profile=getattr(session.config,'_native_profile',None)
    if profile:
        profile.cache_report={**cache.stats,'retained_bytes':cache.bytes,'entries':len(cache.entries)} if cache else {'mode':'off'}
        profile.close(session.config,exitstatus)
