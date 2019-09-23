{{/* vim: set filetype=mustache: */}}

{{- define "dragonchain-k8s.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "helm-toolkit.utils.joinListWithComma" -}}
{{- $local := dict "first" true -}}
{{- range $k, $v := . -}}{{- if not $local.first -}},{{- end -}}"{{- $v -}}"{{- $_ := set $local "first" false -}}{{- end -}}
{{- end -}}
