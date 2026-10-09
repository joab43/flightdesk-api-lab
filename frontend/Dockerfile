# Imagen del frontend: nginx estático + proxy inverso.
# Imagen base estable y específica (pin por versión).
FROM nginx:1.27.3-alpine

# Etiquetas de metadatos (buena práctica de portafolio).
LABEL org.opencontainers.image.title="FlightDesk API Lab - Frontend"
LABEL org.opencontainers.image.description="Interfaz web estática con proxy inverso hacia el backend"
LABEL org.opencontainers.image.version="1.0.0"

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html styles.css app.js /usr/share/nginx/html/

# El usuario "nginx" (UID 101) ya existe en la imagen oficial.
# Los archivos estáticos deben ser legibles por todos.
RUN chmod -R a+rX /usr/share/nginx/html

# nginx escucha en 8080 (ver nginx.conf) para no requerir root.
EXPOSE 8080

# Healthcheck con wget (incluido en busybox de Alpine).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://localhost:8080/ || exit 1

USER nginx

CMD ["nginx", "-g", "daemon off;"]
