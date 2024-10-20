# base image
FROM node:20.11.1

RUN mkdir -p /work/client

# set working directory
WORKDIR /work/client

RUN npm install -g npm@10.9.0

# add `/work/client/node_modules/.bin` to $PATH
ENV PATH /work/client/node_modules/.bin:$PATH

# install and cache app dependencies
COPY client/package-lock.json client/package.json ./

RUN npm install --ignore-optional

COPY client/ ./
COPY deploy_config/files/client.env ../deploy_config/files/client.env

RUN npm run build:deployed

CMD ["npm", "start"]
