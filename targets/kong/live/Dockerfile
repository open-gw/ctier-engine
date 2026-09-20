FROM kong:3.9
USER root
COPY plugin /usr/local/share/lua/5.1/kong/plugins/ctier
COPY estate-probe /usr/local/share/lua/5.1/kong/plugins/ctier-estate-probe
RUN chown -R kong:kong /usr/local/share/lua/5.1/kong/plugins/ctier /usr/local/share/lua/5.1/kong/plugins/ctier-estate-probe
USER kong
ENV KONG_DATABASE=off
ENV KONG_PLUGINS=bundled,ctier,ctier-estate-probe
ENV KONG_DECLARATIVE_CONFIG=/kong/kong.yaml
ENV KONG_PROXY_LISTEN=0.0.0.0:8000
ENV KONG_ADMIN_LISTEN=off
ENV KONG_STATUS_LISTEN=0.0.0.0:8100
ENV KONG_ADMIN_GUI_LISTEN=off
ENV KONG_ANONYMOUS_REPORTS=off
