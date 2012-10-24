from django import template
from django.core import cache
from django.conf import settings

register = template.Library()

DETAILED_STATS = ('redis_version',
                  'connected_clients',
                  'used_cpu_sys',
                  'used_cpu_user',
                  'used_memory_human',
                  'used_memory_peak_human',
                  'max_memory_human',
                  'mem_fragmentation_ratio',
                  'keyspace_hits',
                  'keyspace_misses',
                  'expired_keys',
                  'evicted_keys',)

def _prettyname (name):
    return ' '.join([word.capitalize() for word in name.split('_')])

def _human_bytes (bytes):
    bytes = float(bytes)
    if bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fB' % bytes
    return size

class CacheStats(template.Node):
    """
    Reads the cache stats out of the memcached cache backend. Returns `None`
    if no cache stats supported.
    """
    def render (self, context):
        cache_stats = []
        for cache_name in settings.CACHES.keys():
            c = cache.get_cache(cache_name)
            client = getattr(c, '_client', None)
            clients = [client] if client else getattr(c, 'clients', [])
            for client in clients:
                kw = client.connection_pool.connection_kwargs
                server_data = {'url': 'redis://%s:%s/%s' % (kw.get('host', None) or kw.get('path', ''), kw.get('port', None) or '', kw['db'])}
                server_data['max_memory'] = client.config_get()['maxmemory']
                stats = client.info()
                stats['max_memory_human'] = _human_bytes(server_data['max_memory'])
                server_data['used_memory'] = stats['used_memory']
                server_data['keyspace_misses'] = stats['keyspace_misses']
                server_data['key_operations'] = stats['keyspace_hits'] + stats['keyspace_misses']
                server_data['detailed_stats'] = ((_prettyname(key), stats.get(key, 'Not supported'),) for key in DETAILED_STATS)
                cache_stats.append(server_data)
        context['cache_stats'] = cache_stats
        return ''

@register.tag
def get_cache_stats (parser, token):
    return CacheStats()
