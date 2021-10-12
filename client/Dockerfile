# base image
FROM node:12.22.5

# set working directory
WORKDIR /work

# add `/work/client/node_modules/.bin` to $PATH
ENV PATH /work/client/node_modules/.bin:$PATH

# install and cache app dependencies
COPY client/package-lock.json client/package.json ./client/

WORKDIR /work/client
RUN npm install --ignore-optional

#WORKDIR /work
# COPY deploy deploy/
# COPY client client/
#WORKDIR /work/client

CMD ["npm", "start"]
