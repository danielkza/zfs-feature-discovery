# ZFS Feature Discovery

## Overview

ZFS Feature Discovery for Kubernetes is a companion to [Node Feature Discovery](https://github.com/kubernetes-sigs/node-feature-discovery) to label Nodes with ZFS version, pool and dataset information.

## Status Version

This software is Alpha state. Any feedback is appreciated on refining features and interfaces before v1.0.0.

## Prerequisites

* NFD deployed on each node you want to label with the local source configured
    - See https://github.com/kubernetes-sigs/node-feature-discovery
* `zfsutils`` installed on any node you expected ZFS datasets to be present in. If zfsutils is missing or unavailable, pools and datasets will not be detected correctly, though labels will still be produced with empty/default values for consistency.
    - Custom path for `zfs`, `zpool` and `hostid` commands will be mounted from the host by default when using Helm.
      You can configure them differently if required.

### Node Feature Discovery (NFD)

Make sure NFD is set up and working correctly in your cluster. Check your Nodes for labels starting with
`feature.node.kubernetes.io/` to verify.
Ensure the `local` feature is enabled, and that `/etc/kubernetes/node-feature-discovery/features.d` exists in
your Nodes host filesystem. That will be mounted on `zfs-feature-discovery` containers to generate new labels.
If you change the feature directory, make sure to configure `zfs-feature-discovery` appropriately or it will not work.

### Deploy the Helm chart

See the Helm chart [instructions](deployments/helm/README.md) on how to deploy.
Make sure at least one zpool is defined for the `zfsDiscovery.zpools` value.

After installing, you should now have a `DaemonSet` for `zfs-feature-discovery`
and corresponding Pod running on each of your Nodes.

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
      feature.node.kubernetes.io/zfs-global.hostid=00fac711
      feature.node.kubernetes.io/zfs-global.kver=2.2.2-1
      feature.node.kubernetes.io/zfs-global.ver=2.2.2-1
      feature.node.kubernetes.io/zpool.rpool.ashift=12
      feature.node.kubernetes.io/zpool.rpool.capacity=2
      feature.node.kubernetes.io/zpool.rpool.compatibility=openzfs-2.1-linux
      feature.node.kubernetes.io/zpool.rpool.guid=2706753758230323468
      feature.node.kubernetes.io/zpool.rpool.health=ONLINE
      feature.node.kubernetes.io/zpool.rpool.readonly=off
      feature.node.kubernetes.io/zpool.rpool.size=944892805120
      ...
...
```

## Configuration

When deploying using the Helm chart, configuration in YAML format is generated and attached
as a ConfigMap.

You can also use `extraEnvVarsCM` to pass env vars to override any settings. The env vars
are prefix with `ZFS_FEATURE_DISCOVERY_`.

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
