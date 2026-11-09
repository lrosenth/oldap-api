"""Real Redis cache acceptance for authenticated Jena search and detail reads.

Called only by the owned --cache-only runner. No cache method is mocked and no
shared Redis endpoint is contacted. Mutations use ordinary API routes, except
one explicitly adversarial removal of an asserted resource membership.
"""
import json
import os

from redis import Redis


def check_cache_reads(call, check, create_connection, output, base):
    """Warm shared metadata, then verify identity isolation and fresh permissions.

    Args:
        call: Runner HTTP helper with expected-status assertions.
        check: Runner assertion/report callback.
        create_connection: Actual configured Jena connection factory.
        output: Owned directory for aggregate cache evidence.
        base: URL of the owned API listener for independent concurrent clients.
    """
    cache = Redis.from_url(os.environ['OLDAP_REDIS_URL'])
    try:
        call('PUT', '/admin/datamodel/demo')
        call('PUT', '/admin/datamodel/demo/demo:CachedRecord', {
            'label': ['Cached record@en'], 'superclass': ['oldap:Thing'], 'properties': [
                {'iri': 'demo:caption', 'datatype': 'xsd:string', 'maxCount': 1},
                {'iri': 'demo:parent', 'class': 'demo:CachedRecord', 'maxCount': 1}]})
        call('PUT', '/admin/role/demo/CacheReader', {'label': ['Cache reader@en']})
        call('PUT', '/admin/role/demo/CacheOwner', {'label': ['Cache fixture owner@en']})
        for user, roles in [('cache-reader', {'demo:CacheReader': 'DATA_VIEW'}), ('cache-outsider', {})]:
            call('PUT', '/admin/user/' + user, {'givenName': 'Cache', 'familyName': user,
                'email': user + '@example.org', 'password': 'owned-cache-password',
                'inProjects': [{'project': 'https://example.org/project/demo', 'permissions': []}],
                'hasRole': roles})

        def login(user):
            token = call('POST', '/admin/auth/' + user, {'password': 'owned-cache-password'}).json()['accessToken']
            return {'Authorization': 'Bearer ' + token}

        reader, outsider = login('cache-reader'), login('cache-outsider')
        admin = create_connection(userId='actor', credentials='owned-fixture-password')
        admin.update_query('INSERT DATA { GRAPH <http://oldap.org/base#admin> { '
            '<https://example.org/actor> <http://oldap.org/base#hasRole> <https://example.org/demo/CacheOwner> }}')
        # Preserve independent owner access when revoking the reader's grant.
        grants = {'demo:CacheReader': 'DATA_VIEW', 'demo:CacheOwner': 'DATA_PERMISSIONS'}
        for name in ('parent', 'child'):
            body = {'iri': 'cache-' + name, 'demo:caption': name, 'oldap:attachedToRole': grants}
            if name == 'child':
                body['demo:parent'] = 'demo:cache-parent'
            call('PUT', '/data/demo/demo:CachedRecord', body)
        detail = '/data/demo/demo:cache-child'
        search = '/data/search/demo/class/demo:CachedRecord'
        query = {'filter': [{'property': 'demo:parent', 'op': '==',
                              'value': 'https://example.org/demo/cache-parent', 'type': 'iri'}],
                 'includeProperties': ['demo:caption'], 'sortBy': ['demo:caption|asc'], 'limit': 1}

        def visible(headers, expected):
            rows = call('POST', search, query, headers=headers).json()
            count = call('POST', search, {**query, 'countOnly': True}, headers=headers).json()
            assert len(rows) == expected and count['count'] == expected, (rows, count)
            if expected:
                assert rows[0]['iri'] in ('demo:cache-child', 'https://example.org/demo/cache-child'), rows
            call('GET', detail, headers=headers, status=200 if expected else 404)

        before = cache.info('stats')['keyspace_hits']
        for _ in range(3):
            visible(reader, 1)
        after = cache.info('stats')['keyspace_hits']
        check('Real Redis metadata cache is populated and hit during repeated search/detail reads',
              cache.dbsize() > 0 and after > before)
        visible(outsider, 0)
        visible(reader, 1)
        check('Warm shared cache does not transfer reader access to another identity', True)
        call('POST', detail, {'demo:caption': 'forbidden'}, headers=reader, status=403)
        check('Warm read access does not authorize a write', True)
        call('POST', detail, {'demo:caption': 'fresh caption'})
        check('Warm detail and search projection see committed value updates immediately',
              'fresh caption' in call('GET', detail, headers=reader).text
              and 'fresh caption' in call('POST', search, query, headers=reader).text)
        call('POST', detail, {'oldap:attachedToRole': {'demo:CacheReader': 'DATA_RESTRICTED', 'demo:CacheOwner': 'DATA_PERMISSIONS'}})
        visible(reader, 0)
        check('Object permission downgrade immediately removes warm detail/search/count results', True)
        call('POST', detail, {'oldap:attachedToRole': grants})
        visible(reader, 1)
        check('Restored object permission immediately restores warm reads', True)
        # Keep reification in place to prove that cached metadata and orphaned
        # annotations cannot replace the required asserted membership.
        triple = '<https://example.org/demo/cache-child> <http://oldap.org/base#attachedToRole> <https://example.org/demo/CacheReader>'
        admin.update_query('DELETE DATA { GRAPH <https://example.org/demo/data> { ' + triple + ' }}')
        visible(reader, 0)
        check('Orphaned grant cannot retain access through a warm cache', True)
        admin.update_query('INSERT DATA { GRAPH <https://example.org/demo/data> { ' + triple + ' }}')
        visible(reader, 1)
        call('POST', '/admin/user/cache-reader', {'hasRole': {}})
        # Role changes are applied through current authorization state; they
        # need not invalidate the authentication token itself.
        visible(reader, 0)
        check('Previously issued token immediately observes role removal with warm cache', True)
        reader = login('cache-reader')
        visible(reader, 0)
        check('Fresh login after role removal cannot read previously cached resources', True)
        call('POST', '/admin/user/cache-reader', {'hasRole': {'demo:CacheReader': 'DATA_VIEW'}})
        reader = login('cache-reader')
        visible(reader, 1)
        check('Fresh login after role restoration sees the current authorized result', True)
        from check_cache_concurrency import check_cache_concurrency
        check_cache_concurrency(call, check, base, reader, outsider, detail, search, query, grants, output)
        call('POST', '/admin/user/cache-reader', {'isActive': False})
        # Existing architecture deliberately keeps access JWTs stateless until
        # expiry (15 minutes by default). Deactivation blocks login/refresh,
        # not an already issued token. Do not turn this cache test into an
        # unannounced authentication-policy change.
        call('POST', '/admin/auth/cache-reader', {'password': 'owned-cache-password'}, status=403)
        call('POST', '/admin/auth/refresh', status=401)
        check('Account deactivation blocks new login and refresh despite warm cache', True)
        visible(reader, 1)
        check('Existing access token retains the documented bounded lifetime after deactivation', True)
        (output / 'cache-results.json').write_text(json.dumps({
            'status': 'passed', 'real_redis': True, 'cache_methods_mocked': False,
            'warm_hits_before': before, 'warm_hits_after': after, 'cache_key_count': cache.dbsize(),
            'scope': 'Owned synthetic Jena/Redis; sequential and bounded concurrent API requests; no production cache/load.'
        }, indent=2) + '\n')
    finally:
        cache.close()
