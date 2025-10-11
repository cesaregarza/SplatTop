{{- define "splattop.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "splattop.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "splattop.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "splattop.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "splattop.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "splattop.selectorLabels" -}}
app.kubernetes.io/name: {{ include "splattop.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "splattop.fastapi.matchLabels" -}}
app: {{ default "fast-api-app" .Values.fastApi.podLabel }}
{{- end -}}

{{- define "splattop.react.matchLabels" -}}
app: {{ default "react-app" .Values.react.podLabel }}
{{- end -}}

{{- define "splattop.celeryWorker.matchLabels" -}}
app: {{ default "celery-worker" .Values.celeryWorker.podLabel }}
{{- end -}}

{{- define "splattop.celeryBeat.matchLabels" -}}
app: {{ default "celery-beat" .Values.celeryBeat.podLabel }}
{{- end -}}

{{- define "splattop.redis.matchLabels" -}}
app: {{ default "redis" .Values.redis.podLabel }}
{{- end -}}

{{- define "splattop.splatgpt.matchLabels" -}}
app: {{ default "splatnlp" .Values.splatgpt.podLabel }}
{{- end -}}
