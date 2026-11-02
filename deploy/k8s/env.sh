# Source it in every terminal that talks to the cluster:
#   source deploy/k8s/env.sh
#
# The cluster gets its own kubeconfig, apart from ~/.kube/config, so a command
# typed in the wrong terminal can never reach another cluster (Docker
# Desktop's, or a work one).
# shellcheck shell=bash

export KUBECONFIG="$HOME/.kube/firebreak.yaml"
echo "KUBECONFIG=$KUBECONFIG"
echo "context:    $(kubectl config current-context 2> /dev/null || echo 'none yet, create the cluster first')"
