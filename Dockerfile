FROM golang:1.10-alpine3.7 AS gobuild

# copy credentials to .ssh
COPY .ssh/* /root/.ssh/
RUN chmod 0600 /root/.ssh/*
RUN ls -l /root/.ssh

# install git
RUN apk add --no-cache git openssh-client
# add aws ssh keys
ENV AWSCC="git-codecommit.us-east-1.amazonaws.com"
RUN touch /root/.ssh/known_hosts && ssh-keygen -R ${AWSCC}
RUN ssh-keyscan -t rsa ${AWSCC} >> ~/.ssh/known_hosts

# install glide and dep
RUN go get github.com/Masterminds/glide
RUN go get github.com/golang/dep/cmd/dep

# build chaos-go
ARG CHAOS_GO_REPO="ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/chaos-go"
ARG CHAOS_GO_LOGICAL="gitlab.ndau.tech/experiments/chaos-go"
ARG CHAOS_GO_LABEL="master"

ENV CHAOS_GO_PATH=${GOPATH}/src/${CHAOS_GO_LOGICAL}
RUN mkdir -p $(dirname ${CHAOS_GO_LOGICAL}) && \
    git clone ${CHAOS_GO_REPO} ${CHAOS_GO_PATH}
WORKDIR ${CHAOS_GO_PATH}
RUN git checkout ${CHAOS_GO_LABEL} && \
    glide install && \
    CGO_ENABLED=0 GOOS=linux go install -a -ldflags '-extldflags "-static"' ./cmd/chaosnode && \
    cp ${GOPATH}/bin/chaosnode /bin/ && \
    cp -r ${CHAOS_GO_PATH}/py /gen-nodes

# build chaostool
ARG CHAOSTOOL_REPO="ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/chaostool"
ARG CHAOSTOOL_LOGICAL="gitlab.ndau.tech/experiments/chaostool"
ARG CHAOSTOOL_LABEL="master"

ENV CHAOSTOOL_PATH=${GOPATH}/src/${CHAOSTOOL_LOGICAL}
RUN mkdir -p $(dirname ${CHAOSTOOL_LOGICAL}) && \
    git clone ${CHAOSTOOL_REPO} ${CHAOSTOOL_PATH}
WORKDIR ${CHAOSTOOL_PATH}
RUN git checkout ${CHAOSTOOL_LABEL} && \
    glide install && \
    CGO_ENABLED=0 GOOS=linux go install -a -ldflags '-extldflags "-static"' ./cmd/chaos && \
    cp ${GOPATH}/bin/chaos /bin/

# build ndwhitelist
ARG WHITELIST_REPO="ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/whitelist"
ARG WHITELIST_LOGICAL="gitlab.ndau.tech/experiments/whitelist"
ARG WHITELIST_LABEL="master"

ENV WHITELIST_PATH=${GOPATH}/src/${WHITELIST_LOGICAL}
RUN mkdir -p $(dirname ${WHITELIST_LOGICAL}) && \
    git clone ${WHITELIST_REPO} ${WHITELIST_PATH}
WORKDIR ${WHITELIST_PATH}
RUN git checkout ${WHITELIST_LABEL} && \
    dep ensure && \
    CGO_ENABLED=0 GOOS=linux go install -a -ldflags '-extldflags "-static"' ./cmd/ndwhitelist && \
    cp ${GOPATH}/bin/ndwhitelist /bin/

FROM python:3.6-alpine3.7

COPY --from=gobuild /bin/chaosnode /bin/
COPY --from=gobuild /bin/chaos /bin/
COPY --from=gobuild /bin/ndwhitelist /bin/
COPY --from=gobuild /gen-nodes/ /

# get dependencies and useful tools
RUN pip3 install pipenv pytest && \
    apk add --no-cache jq sed docker

COPY tests /integration-tests
WORKDIR /integration-tests
RUN pipenv sync
CMD ["pipenv", "run", "pytest"]
