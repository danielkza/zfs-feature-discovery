{{/* vim: set filetype=mustache: */}}
{{- define "zfs-feature-discovery.configMap.config.name" -}}
{{ include "common.names.fullname" . }}-config
{{- end -}}

{{- define "zfs-feature-discovery.configMap.zfsbin.name" -}}
{{ include "common.names.fullname" . }}-zfs-bin
{{- end -}}

{{- define "zfs-feature-discovery.zfsProps" -}}
{{- range $prop = . }}
- {{ $prop | quote }}
{{- end }}
{{- end }}

{{- define "zfs-feature-discovery.config.zpools" -}}
{{- if empty .zpools -}}
{{- fail "zfs-feature-discovery: `zpools` must not be empty" -}}
{{- end -}}
{{ .zpools | toYaml }}
{{- end -}}

{{- define "zfs-feature-discovery.config" -}}
{{- if .zfs.command }}
zfs_command: {{ .zfs.command | quote }}
{{- end }}
{{- if .zpool.command }}
zpool_command: {{ .zpool.command | quote }}
{{- end }}
{{- if .hostid.command }}
hostid_command: {{ .hostid.command | quote }}
{{- end }}
zpools: {{- include "zfs-feature-discovery.config.zpools" . | nindent 2 }}
{{- if not (empty .zpool.props) }}
zpool_props: {{- toYaml .zpool.props | nindent 2 }}
{{- end }}
{{- if not (empty .zfs.props) }}
zfs_props: {{- toYaml .zfs.props | nindent 2 }}
{{- end }}
feature_dir: {{ .hostFeatureDir | quote }}
label:
  {{- if .nodeLabels.namespace }}
  namespace: {{ .nodeLabels.namespace | quote }}
  {{- end }}
  {{- if .nodeLabels.datasetLabelFormat }}
  zfs_dataset_format: {{ .nodeLabels.nodeLabelFormat | quote }}
  {{- end }}
  {{- if .nodeLabels.datasetLabelFormat }}
  zpool_dataset_format: {{ .nodeLabels.nodeLabelFormat | quote }}
  {{- end }}
{{- end -}}

{{- define "zfs-feature-discovery.podAnnotations" -}}
{{- $annotations := mergeOverwrite .Values.commonAnnotations .Values.podAnnotations -}}
{{- if not (empty $annotations) -}}
{{- toYaml $annotations | trim }}
{{- end -}}
rollme: {{ randAlphaNum 5 | quote }}
{{- end -}}

{{- define "zfs-feature-discovery.hostBinWrapperScript" -}}
#!/bin/sh
if [ -f "/host/{{ .hostBin }}" ]; then
  exec chroot /host "{{ .hostBin }}" "$@"
else
  exec chroot /host /bin/sh -c '{{ .name }} "$@"' "$@"
fi
{{- end -}}
