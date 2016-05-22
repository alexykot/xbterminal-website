redis-server:
  pkg:
    - installed
  service.running:
    - enable: true
    - require:
      - pkg: redis-server
    - watch:
      - file: /etc/redis/redis.conf

redis.conf:
  file.managed:
    - name: /etc/redis/redis.conf
    - source: salt://redis/redis.conf
    - require:
      - pkg: redis-server
