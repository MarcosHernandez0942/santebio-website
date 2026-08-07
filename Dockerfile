FROM nginx:alpine

COPY clone/ /usr/share/nginx/html/

EXPOSE 80
