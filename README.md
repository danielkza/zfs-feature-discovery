# ZFS Feature Discovery

[![Go Report Card](https://goreportcard.com/badge/github.com/NVIDIA/gpu-feature-discovery)](https://goreportcard.com/report/github.com/NVIDIA/gpu-feature-discovery)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Table of Contents

- [Overview](#overview)
- [Beta Version](#beta-version)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  * [Node Feature Discovery (NFD)](#node-feature-discovery-nfd)
  * [Deploying](#deploy-nvidia-gpu-feature-discovery-gfd)
    + [Daemonset](#daemonset)
  * [Verifying Everything Works](#verifying-everything-works)
- [Configuration](#the-gfd-command-line-interface)
- [Generated Labels](#generated-labels)
- [Deployment via `helm`](#deployment-via-helm)
- [Building and running locally with Docker](#building-and-running-locally-with-docker)
- [Building and running locally on your native machine](#building-and-running-locally-on-your-native-machine)

## Overview

ZFS GPU Feature Discovery for Kubernetes is a companion to [Node Feature Discovery](https://github.com/kubernetes-sigs/node-feature-discovery) to label Nodes with ZFS pool and dataset information.

## Status Version

This software is Alpha-state. Any feedback is appreciated on refining features and interfaces before v1.0.0.

## Prerequisites

* NFD deployed on each node you want to label with the local source configured
    - See https://github.com/kubernetes-sigs/node-feature-discovery
* `zfsutils`` installed on any node you expected ZFS datasets to be present in. If zfsutils is missing or unavailable, pools and datasets will not be detected correctly, though labels will still be produced with empty/default values.
    - Custom path for `zfs` and `zpool` commands can be configured if required.

## Quick Start

The following assumes you have at least one node in your cluster with GPUs and
the standard NVIDIA [drivers](https://www.nvidia.com/Download/index.aspx) have
already been installed on it.

### Node Feature Discovery (NFD)

Make sure NFD is set up and working correctly in your cluster. Check your Nodes for labels starting with
`feature.node.kubernetes.io/` to verify.
Ensure the `local` feature is enabled, and that `/etc/kubernetes/node-feature-discovery/features.d` exists in
your Nodes host filesystem. That will be mounted on `zfs-feature-discovery` containers to generate new labels.
If you change the feature directory, make sure to configure `zfs-feature-discovery` appropriately or it will not work.

### Deploy the Helm chart

See the Helm chart [instructions](deployments/helm/README.md) for available values.
Deploy the Helm chart. You should now have a `DaemonSet` configured and running on each
of your Nodes.

Note: deployment methods other than `DaemonSet` are not yet available.

### Verifying Everything Works

You should now be able to see new labels in your Nodes;

```
$ kubectl get nodes -o yaml
apiVersion: v1
items:
- apiVersion: v1
  kind: Node
  metadata:
    ...

    labels:
      openzfs.org/zpool/
      TODO: label examples
      ...
...
```

## Configuration

`zfs-feature-discovery` is configured through env variables prefixed with `ZFS_FEATURE_DISCOVERY`.
By default, these are sourced from a `ConfigMap` for ease of use, with values filled from Helm values.

TODO: add env vars


## Contributing

### Docker builds

To build the standard Docker image run the following from the root of the repository:

```
cd zfs-feature-discovery
docker build -f docker/Dockerfile -t zfs-feature-discovery
```

To build a development image and mount the source directory to it, you can do:

```
cd zfs-feature-discovery
docker build -f docker/Dockerfile -t zfs-feature-discovery-devel
docker run -it --mount=$PWD:/src zfs-feature-discovery-devel /bin/bash
```

### Running tests

You can use `pytest` to run tests after you have set up the package.

If you want to do it locally, create a virtualenv, then install the dependencies and run tests:

```
cd zfs-feature-discovery
pip install -e '.[test]'
pytest
```

## License

This software is available under the terms of the Apache 2.0 License. See attached [license](LICENSE.md) for details.
