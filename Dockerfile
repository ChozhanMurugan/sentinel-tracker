FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy all frontend files
COPY index.html /usr/share/nginx/html/index.html
COPY js /usr/share/nginx/html/js
COPY styles /usr/share/nginx/html/styles

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
