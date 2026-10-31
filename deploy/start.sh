#!/bin/bash
# First boot: create the database (company Brightloop Software, India/INR, attachments
# stored in PostgreSQL because the free host's disk is wiped on restart), then install
# the module. Later boots: just start Odoo.
set -e
: "${PORT:=8069}"
: "${DB_PORT:=5432}"
ARGS=(--db_host="$DB_HOST" --db_port="$DB_PORT" --db_user="$DB_USER" --db_password="$DB_PASSWORD"
      --database="$DB_NAME" --db-filter="^${DB_NAME}\$" --no-database-list
      --proxy-mode --workers=0 --max-cron-threads=1 --without-demo=all)
export PGPASSWORD="$DB_PASSWORD"
state() {
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "select state from ir_module_module where name='$1'" 2>/dev/null || true
}
if [ "$(state brightloop_subscription)" = "installed" ]; then
  exec odoo "${ARGS[@]}" --http-port="$PORT"
fi
if [ "$(state base)" != "installed" ]; then
  echo "==> Creating database"
  odoo "${ARGS[@]}" -i base --stop-after-init --no-http
  odoo shell "${ARGS[@]}" --no-http < /opt/brightloop/setup.py
fi
echo "==> Installing Brightloop Subscriptions (web server is already listening)"
exec odoo "${ARGS[@]}" --http-port="$PORT" -i brightloop_subscription
