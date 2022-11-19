# fantasy_football_records

[We're live!!](https://walpolefantasyfootball.com/)

### Setup

- [Namecheap domain to Digital Ocean](https://www.namecheap.com/support/knowledgebase/article.aspx/10375/2208/how-do-i-link-a-domain-to-my-digitalocean-account/)
- [Digital Ocean starter guide](https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-22-04)
- [Digital Ocean flask + nginx](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-22-04)

### Notes

Get access to private leagues that you are a member of with the instructions on [cwendt94's awesome ESPN API repo](https://github.com/cwendt94/espn-api)

My `sudo ufw status` output to allow only SSH, HTTP, and HTTP traffic to the Digital Ocean droplet

```
To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere                  
Nginx HTTPS                ALLOW       Anywhere                  
80/tcp                     ALLOW       Anywhere                  
OpenSSH (v6)               ALLOW       Anywhere (v6)             
Nginx HTTPS (v6)           ALLOW       Anywhere (v6)             
80/tcp (v6)                ALLOW       Anywhere (v6)
```

My `/etc/nginx/sites-available/<name>` addition (after certbot did most of the setup) to redirect HTTP traffic to HTTPS

```
server {
    listen 80;
    server_name _;
    if ($scheme = "http") {
        return 301 https://$host$request_uri;
    }
}
```
