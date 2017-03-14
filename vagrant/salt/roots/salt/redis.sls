redis_package:
  pkg:
    - installed
    - name: redis-server

redis_config:
  file.managed:
    - name: /etc/redis/redis.conf
    - source: salt://redis/redis.conf
    - require:
      - pkg: redis_package

redis_service:
  service.running:
    - name: redis-server
    - enable: true
    - require:
      - pkg: redis_package
    - watch:
      - file: redis_config
