FROM ubuntu

RUN apt-get update

ARG TZ
ENV TZ ${TZ}
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update
RUN apt-get -y install git

RUN apt-get install -y apt-utils vim curl apache2 apache2-utils

RUN apt-get -y install python3 libapache2-mod-wsgi-py3

# Install ModSecurity
RUN apt-get update
RUN apt-get -y install libapache2-mod-security2 

# Configure ModSecurity
RUN cp /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf
RUN sed 's/SecRuleEngine DetectionOnly/SecRuleEngine On/g' /etc/modsecurity/modsecurity.conf

# Download and Configure ModSecurity Core Rule
# remove the old rules 
RUN rm -rf /usr/share/modsecurity-crs  
#  install new ones
RUN git clone https://github.com/SpiderLabs/owasp-modsecurity-crs.git /usr/share/modsecurity-crs
RUN cp /usr/share/modsecurity-crs/crs-setup.conf.example /usr/share/modsecurity-crs/crs-setup.conf
RUN sed -i -e 's/DetectionOnly$/On/i' /etc/modsecurity/modsecurity.conf
# enable this rule set in apache configuration
ADD ./configuration/security2.conf /etc/apache2/mods-enabled/security2.conf

# enable the Apache header module 
RUN a2enmod headers

RUN ln /usr/bin/python3 /usr/bin/python
RUN apt-get -y install python3-pip
RUN ln /usr/bin/pip3 /usr/bin/pip
RUN pip install --upgrade pip
RUN pip install django ptvsd


COPY ./www /var/www

WORKDIR /var/www

RUN pip install -r requirements.txt


RUN find /var/www/ -type d -exec chmod 755 {} \; &&\
    find /var/www/ -type f -exec chmod 644 {} \;
RUN find /etc/apache2/ -type d -exec chmod 755 {} \; &&\
    find /etc/apache2/ -type f -exec chmod 644 {} \;


# give access to /var/www/forecast/django.log
RUN chown www-data /var/www/debug.log

ADD ./configuration/forecast_apache2.conf /etc/apache2/apache2.conf
ADD ./configuration/forecast_site.conf /etc/apache2/sites-available/000-default.conf
ADD ./configuration/forecast_security.conf /etc/apache2/conf-enabled/security.conf 

ARG SERVER_NAME
ENV SERVER_NAME ${SERVER_NAME}

RUN chmod a+x entrypoint.sh
RUN bash entrypoint.sh ${SERVER_NAME}

ARG APP_PORT
ENV APP_PORT ${APP_PORT}

# apache corre en el puerto 80 el cual está expuesto al puerto definido en el yml
EXPOSE 80 ${APP_PORT}

CMD ["apache2ctl", "-D", "FOREGROUND"]
