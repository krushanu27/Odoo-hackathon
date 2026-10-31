# Brightloop Subscriptions on any Docker host (Render free plan via render.yaml)
FROM odoo:19
USER root
COPY brightloop_subscription /mnt/extra-addons/brightloop_subscription
COPY deploy/start.sh deploy/setup.py /opt/brightloop/
RUN sed -i 's/\r$//' /opt/brightloop/start.sh && chmod +x /opt/brightloop/start.sh
USER odoo
ENTRYPOINT ["/opt/brightloop/start.sh"]
