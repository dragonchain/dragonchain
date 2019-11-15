#!/bin/sh

command_spacers() {
    sleep 2
    echo "============================================================" # 60 
}

# set vars
start=$(date +%s)
DCID=69f29b3c-f49c-483e-bf26-5c33e3f774e3

# deploy code
./scripts/build_containers.sh
command_spacers

# write name of old TP pod to variable
TPold=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/processor/ {print $1}')

# bounce transaction processor pod
kubectl delete po --grace-period=0 -n dragonchain "$TPold" # &  # '&' param runs cmd in background...
PID=%!  # PID of the last command launched in the script
sleep 2
kill "$PID"
command_spacers
# FIXME: kill command not working properly; script will currently hang, 
#        waiting for kubectl call to complete (graceful failure, script still works OK)

# write name of new TP pod to variable
TPnew=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/processor/ {print $1}')

# wait until transaction processor pod is restarted
podStatus=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/'"$TPnew"'/ {print $3}')
echo "new TP pod status: $podStatus"
while [ "$podStatus" != "Running" ]
do
    echo "Waiting for the new transaction processor pod to be running..."
    podStatus=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/'"$TPnew"'/ {print $3}')
    sleep 2
done
command_spacers

# wait until transaction processor is ready
podStatus=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/'"$TPnew"'/ {print $2}')
echo "new TP pod status: $podStatus"
while [ "$podStatus" != "1/1" ]
do
    echo "Waiting for the new transaction processor pod to be ready..."
    podStatus=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/'"$TPnew"'/ {print $2}')
    sleep 2
done
command_spacers

# wait until old TP pod is terminated
podExists=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/'"$TPold"'/ {print $1}')
echo "does old TP pod exist? : $podExists"
while [ "$podExists" = "$TPold" ]
do
    echo "Waiting for old transaction processor pod to terminate..."
    podExists=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/'"$TPold"'/ {print $1}')
    sleep 2
done
command_spacers

end=$(date +%s)
runtime=$((end-start))
echo "Runtime: ~$runtime seconds"
echo "Displaying log..."
command_spacers

# write name of new TP pod to variable
TP=$(kubectl get pod -n dragonchain -l dragonchainId="$DCID" | awk '/processor/ {print $1}')
# follow the new TP pod's log
kubectl logs "$TP" -n dragonchain -f