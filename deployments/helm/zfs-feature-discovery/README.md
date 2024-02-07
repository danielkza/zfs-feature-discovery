# zfs-feature-discovery

## Provenance

This Helm chart is based on code from https://github.com/NVIDIA/gpu-feature-discovery and https://github.com/openebs/zfs-localpv

## Installation Example

```
cat > my-values.yaml <<EOF
zfsDiscovery:
  zpools:
    rpool: ["my/dataset", "my/other/dataset"]
    dpool: []
EOF

helm repo add zfs-feature-discovery https://danielkza.github.io/zfs-feature-discovery
helm install zfs-feature-discovery zfs-feature-discovery/zfs-feature-discovery -f my-values.yaml
```

## Parameters

### Image settings

| Name                      | Description                                                                                                           | Value                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `global.imageRegistry`    | Global Docker image registry                                                                                          | `""`                                      |
| `global.imagePullSecrets` | Global Docker registry secret names as an array                                                                       | `[]`                                      |
| `image.registry`          | zfs-feature-discovery image registry                                                                                  | `ghcr.io`                                 |
| `image.repository`        | zfs-feature-discovery image repository                                                                                | `ghcr.io/danielkza/zfs-feature-discovery` |
| `image.tag`               | zfs-feature-discovery Image tag (immutable tags are recommended)                                                      | `0.0.2`                                   |
| `image.digest`            | zfs-feature-discovery image digest in the way sha256:aa.... Please note this parameter, if set, will override the tag | `""`                                      |
| `image.pullPolicy`        | zfs-feature-discovery image pull policy                                                                               | `IfNotPresent`                            |
| `image.pullSecrets`       | zfs-feature-discovery image pull secrets                                                                              | `[]`                                      |

### zfs-feature-discovery parameters

| Name                                   | Description                                                                                                                                                                                   | Value                                               |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `zfsDiscovery.zpools`                  | Map from zpools names to dataset names datasets to monitor. If a zpool is present with empty datasets, only collect zpool information for it. Example: {"rpool": ["ds1", "ds2"], "dpool": []} | `{}`                                                |
| `zfsDiscovery.nodeLabels.zfsFormat`    | Format string to generate dataset property labels. Do not include the namespace. Available placeholders: pool_name, dataset_name, property_name                                               | `"zfs.{pool_name}.{dataset_name}.{property_name}"`  |
| `zfsDiscovery.nodeLabels.zpoolFormat`  | Format string to generate pool property labels. Do not include the namespace. Available placeholders: pool_name, property_name                                                                | `"zpool.{pool_name}.{property_name}"`               |
| `zfsDiscovery.nodeLabels.globalFormat` | Format string to generate pool property labels. Do not include the namespace. Available placeholders: property_name                                                                           | `"zfs-global.{property_name}"`                      |
| `zfsDiscovery.nodeLabels.namespace`    | Namespace prefix for generated labels. Don't include a trailin slash.                                                                                                                         | `feature.node.kubernetes.io`                        |
| `zfsDiscovery.zfs.hostBin`             | Path *from the host* to zfs binary.                                                                                                                                                           | `/usr/sbin/zfs`                                     |
| `zfsDiscovery.zfs.command`             | Path *in the container* to zfs binary. Don't change unless you have a good reason to.                                                                                                         | `/usr/local/bin/host-zfs`                           |
| `zfsDiscovery.zfs.props`               | Dataset properties to generate labels for. This is additive by default. Use "-some_prop" (or "-all") to remove pre-included properties.                                                       | `[]`                                                |
| `zfsDiscovery.zpool.hostBin`           | Path *from the host* to zpool binary.                                                                                                                                                         | `/usr/sbin/zpool`                                   |
| `zfsDiscovery.zpool.command`           | Path *in the container* to zfs binary. Don't change unless you have a good reason to.                                                                                                         | `/usr/local/bin/host-zpool`                         |
| `zfsDiscovery.zpool.props`             | Pool properties to generate labels for. This is additive by default. Use "-some_prop" (or "-all") to remove pre-included properties.                                                          | `[]`                                                |
| `zfsDiscovery.hostid.hostBin`          | Path *from the host* to hostid binary.                                                                                                                                                        | `/usr/bin/hostid`                                   |
| `zfsDiscovery.hostid.command`          | Path *in the container* to hostid binary. Don't change unless you have a good reason to.                                                                                                      | `/usr/local/bin/host-hostid`                        |
| `zfsDiscovery.sleepInterval`           | How frequently to re-generate features, in seconds                                                                                                                                            | `60`                                                |
| `zfsDiscovery.hostFeatureDir`          | Host directory to write features in. Don't change unless you have a good reason to.                                                                                                           | `/etc/kubernetes/node-feature-discovery/features.d` |
| `zfsDiscovery.logLevel`                | Log level                                                                                                                                                                                     | `INFO`                                              |

### Common parameters

| Name                        | Description                                                                                                              | Value                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| `nameOverride`              | String to partially override external-dns.fullname template (will maintain the release name)                             | `""`                   |
| `fullnameOverride`          | String to fully override external-dns.fullname template                                                                  | `""`                   |
| `commonLabels`              | Labels to add to all deployed objects                                                                                    | `{}`                   |
| `commonAnnotations`         | Annotations to add to all deployed objects                                                                               | `{}`                   |
| `extraDeploy`               | Array of extra objects to deploy with the release (evaluated as a template).                                             | `[]`                   |
| `hostAliases`               | Deployment pod host aliases                                                                                              | `[]`                   |
| `updateStrategy`            | update strategy type                                                                                                     | `undefined`            |
| `command`                   | Override default command                                                                                                 | `[]`                   |
| `args`                      | Override default args                                                                                                    | `[]`                   |
| `lifecycleHooks`            | Override default etcd container hooks                                                                                    | `{}`                   |
| `schedulerName`             | Alternative scheduler                                                                                                    | `""`                   |
| `topologySpreadConstraints` | Topology Spread Constraints for pod assignment                                                                           | `[]`                   |
| `replicaCount`              | Desired number of ExternalDNS replicas                                                                                   | `1`                    |
| `podAffinityPreset`         | Pod affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                      | `""`                   |
| `podAntiAffinityPreset`     | Pod anti-affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                 | `soft`                 |
| `nodeAffinityPreset`        | Node affinity preset                                                                                                     | `{}`                   |
| `affinity`                  | Affinity for pod assignment                                                                                              | `{}`                   |
| `nodeSelector`              | Node labels for pod assignment                                                                                           | `{}`                   |
| `tolerations`               | Tolerations for pod assignment                                                                                           | `[]`                   |
| `podAnnotations`            | Additional annotations to apply to the pod.                                                                              | `{}`                   |
| `podLabels`                 | Additional labels to be added to pods                                                                                    | `{}`                   |
| `priorityClassName`         | priorityClassName                                                                                                        | `system-node-critical` |
| `containerSecurityContext`  | Define the Container's  Security Context, see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ | `{}`                   |
| `podSecurityContext`        | Define the Pods's  Security Context, see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/      | `{}`                   |
| `resources.limits`          | see ref: https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/                           | `{}`                   |
| `resources.requests`        | see ref: https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/                           | `{}`                   |
| `livenessProbe`             | Override default liveness probe                                                                                          | `{}`                   |
| `readinessProbe`            | Override default readiness probe                                                                                         | `{}`                   |
| `startupProbe`              | Override default startup probe                                                                                           | `{}`                   |
| `customLivenessProbe`       | Override default liveness probe                                                                                          | `{}`                   |
| `customReadinessProbe`      | Override default readiness probe                                                                                         | `{}`                   |
| `customStartupProbe`        | Override default startup probe                                                                                           | `{}`                   |
| `extraVolumes`              | A list of volumes to be added to the pod                                                                                 | `[]`                   |
| `extraVolumeMounts`         | A list of volume mounts to be added to the pod                                                                           | `[]`                   |
| `podDisruptionBudget`       | Configure PodDisruptionBudget                                                                                            | `{}`                   |
