from kubernetes import dynamic as kube_dynamic
from kubernetes import watch as kube_watch
import kubernetes
import logging
import datetime
from random import shuffle
import concurrent.futures


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# Small function to replicate the "random selection" currently used by the CloudSure pod-delete tests.
def select_random_from_list(items, **kwargs):
    """
    Returns list of randomly selected members, in a random order.  At least 1 item will always be returned,
    and all values are rounded up for example:

    1% of 4 items will return 1
    30% of 4 items (1.2) will return 2 items
    51% of 4 items will return 3
    76% of 4 items will return all 4

    If no kwargs are supplied, the entire list is returned randomized.

    Agrs:
        items: a list of items. (usually a pod list in this context.)

    kwargs:
        percent: select a percentage of the supplied list
        count: select a specificed number of items from the supplied list.

    Returns: (list)
    """
    # shuffle 2x just for good measure.
    shuffle(items)
    shuffle(items)

    if 'percent' in kwargs:
        num_items = len(items) * (float(kwargs['percent']) / 100.0)
        if int(num_items) < num_items:
            num_items = int(num_items) + 1
    elif 'count' in kwargs:
        num_items = kwargs['count']
    else:
        num_items = len(items)

    # to cover bad input cases like negative numbers.
    if num_items < 1:
        num_items = 1

    return items[0:num_items]


def label_dict_to_selector(labels):
    """
    Converts a dict of labels into a label_selector (i.e. "k1=v1,k2=v2")

    Positional Arguments:
        labels: (dict)  Dict of <label>:<value> k:v pairs

    Return: (str) label_selector string.
    """
    # If labels is already a string, it is probably already a label selector, just return it.
    if isinstance(labels, str):
        return labels
    # If labels is a dict, convert the k:v into a comma separated string of 'k=v' entries.
    if isinstance(labels, dict):
        label_list = [k + "=" + v for k, v in labels.items()]
        selector = ",".join(label_list)
        log.debug('Converting labels to label_selector - %s', labels)
        log.debug('label_selector - %s', selector)
        return selector
    # labels was not a string, or a dict.  Return an empty string.
    return ''

class PodDelete:
    def __init__(self, client_config):
        # TODO:  This kubernetes client stuff is really messed up.  Need to fix this so that it only uses
        #        ONE of the available client interfaces.  Because the different clients use different
        #        models, they cannot be used interchangeably.

        # TODO:  Fix the config load so that is comes from an argument, or an authenticated and already
        #        usable client is passed in.

        kubernetes.config.load_kube_config()
        self._kube_client = kubernetes.client.ApiClient()
        self._dc = kubernetes.dynamic.DynamicClient(self._kube_client)
        self._core = kubernetes.client.CoreV1Api()
        self._apps = kubernetes.client.AppsV1Api()

    def _resource_client(self, kind):
        try:
            res_clnt = self._dc.resources.get(kind=kind)
        except kube_dynamic.exceptions.ResourceNotFoundError as e:
            log.error('The "kind" %s is invalid', kind)
            return False
        except Exception as e:
            log.error('Unknown error tyring to obtain client for "kind" %s', kind)
            log.error(e)
            return False
        return res_clnt


    def _resource_get(self, kind, namespace, name='', labels: dict = None, suppress_errors=False):
        client = self._resource_client(kind)
        try:
            label_selector = label_dict_to_selector(labels)
            log.debug('Getting %s %s from namespace %s with labels %s', kind, name, namespace, label_selector)
            response = client.get(name=name, namespace=namespace, label_selector=label_selector)
            """
            ###  This was added as part of a troubleshooting effort.  But it wasnt where the problem ended up
            ###  being.  The client seems to behave as expected when empty strings are passed.
            
            if labels:
                label_selector = label_dict_to_selector(labels)
                if name:
                    log.debug('Getting %s %s from namespace %s with labels %s', kind, name, namespace, label_selector)
                    response = client.get(name=name, namespace=namespace, label_selector=label_selector)
                else:
                    log.debug('Getting %s from namespace %s with labels %s', kind, namespace, label_selector)
                    response = client.get(namespace=namespace, label_selector=label_selector)
            elif name:
                log.debug('Getting %s %s from namespace %s', kind, name, namespace)
                response = client.get(name=name, namespace=namespace)
            else:
                log.error('At least one of Name or Labels must be specified')
                return False
            """
        except kube_dynamic.exceptions.NotFoundError as e:
            if not suppress_errors:
                log.error('Resource kind: %s, name: %s, namespace: %s -- Was not found', kind, name, namespace)
            return False
        except Exception as e:
            if not suppress_errors:
                log.error('Unknown Exception occurred trying to get resource')
                log.error(e)
            return False
        return response


    def pods_for_controller(self, kind, name, namespace):
        """
        pods_for_controller

        Obtains a list of pods associated with the specified Deployment or StatefulSet.

        :param kind: (str) Kind of Controller (Deployment | StatefulSet)
        :param name: (str) Name of the Deployment or StatefulSet
        :param namespace: (str) Name of the Namespace.
        :return: (list) List of (<name>,<namespace>) tuples.
        """
        ctlr = self._resource_get(kind, namespace, name=name)
        pods = self._resource_get('Pod', namespace, labels=ctlr.spec.selector.matchLabels)
        return [(p.metadata.name, p.metadata.namespace) for p in pods.items]

    def _wait_for_pod_delete(self, names, namespace, timeout=0):
        # TODO: Fix timeout.  Adding timeouts to the watch broke things, I just removed it for now.
        """
        _wait_for_pod_delete

        Waits for the specified list of pods to delete.  This will wait until the pods are removed from the Kubernetes
        ETCd server/API.

        :param names: (list)  List of Pod names to delete
        :param namespace: (str) Namespace of the pods to delete
        :param timeout: (int) Wait timeout in seconds.
        :return: (list) List of event tuples (<Pod_name>, <timestamp>, <kind>, <event>)
        """
        log.debug('Starting _wait_for_pod_delete for %s in namespace %s', names, namespace)
        delete_time = []
        w = kube_watch.Watch()
        for event in w.stream(self._core.list_namespaced_pod, namespace=namespace):  # , timeout=timeout):
            log.debug("WAIT POD DELETE Event: %s %s %s" % (event['type'], event['object'].kind, event['object'].metadata.name))
            if event['object'].metadata.name in names:
                if event['type'] == 'DELETED':
                    # TODO: This event needs to go to a result handler.
                    delete_time.append((event['object'].metadata.name, datetime.datetime.now(), 'Pod', 'Deleted'))
                    log.info('Pod %s in namespace %s has been deleted at %s', event['object'].metadata.name, namespace, delete_time)
            if set([i[0] for i in delete_time]) == set(names):
                log.info('All Pods have been deleted')
                w.stop()
        return delete_time

    def _wait_for_pod_ready(self, names, namespace, not_uids=None, timeout=0):
        # TODO: Fix timeout.  Adding timeouts to the watch broke things, I just removed it for now.
        """
        _wait_for_pod_ready

        Waits for all pods to be in ready state. If not_uids dict is supplied, it will wait until the pods that are ready,
        are NOT the original pods. (i.e. pod must be deleted, re-created, and then become ready).

        :param names: (list)  List of Pod names to delete
        :param namespace: (str) Namespace of the pods to delete
        :param timeout: (int) Wait timeout in seconds.
        :param not_uids: (dict) Dict containing UIDs of the original pods.
        :return: (list) List of event tuples (<Pod_name>, <timestamp>, <kind>, <event>)
        """
        def pod_has_old_uid(obj):
            """
            pod_has_old_uid - sub-function of _wait_for_pod_ready

            Determines if the identified pod matches its 'not_uid'

            :param obj: (Pod)
            :return: (bool)
            """
            if not_uids:
                if obj.metadata.namespace in not_uids:
                    if obj.metadata.name in not_uids[obj.metadata.namespace]:
                        if obj.metadata.uid != not_uids[obj.metadata.namespace][obj.metadata.name]:
                            log.debug('UID for pod %s in namespace %s does not mach, this is a new pod (obj: %s, not_uid: %s)',
                                      obj.metadata.name, obj.metadata.namespace,
                                      obj.metadata.uid, not_uids[obj.metadata.namespace][obj.metadata.name])
                            return False
                        else:
                            log.debug('UID for pod %s in namespace %s matches, this is the old pod (obj: %s, not_uid: %s)',
                                      obj.metadata.name, obj.metadata.namespace,
                                      obj.metadata.uid, not_uids[obj.metadata.namespace][obj.metadata.name])
            else:
                log.debug('No "not_uid" supplied for pod ready.  Accepting any ready state.')
            return True
        def pod_ready(obj):
            """
            pod_ready - sub-function of _wait_for_pod_ready

            Determines if a pod is in "Ready" state"

            :param obj: (Pod)
            :return: (bool)
            """
            if obj.status.conditions:
                ready_cond = [s for s in obj.status.conditions if s.type == 'Ready']
                if len(ready_cond) > 0:
                    log.debug('Pod Condition for %s in namespace %s is %s', obj.metadata.name, obj.metadata.namespace, ready_cond)
                    if ready_cond[0].status == 'True':
                        return True
                else:
                    log.debug('No READY condition in pod status.')
            return False
        ready_time = []
        w = kube_watch.Watch()
        for event in w.stream(self._core.list_namespaced_pod, namespace=namespace): #  , timeout=timeout):
            log.debug("WAIT POD READY Event: %s %s %s" % (event['type'], event['object'].kind, event['object'].metadata.name))
            if event['object'].metadata.name in names and not pod_has_old_uid(event['object']):
                if pod_ready(event['object']):
                    # TODO: Send Event to Results Handler.
                    ready_time.append((event['object'].metadata.name, datetime.datetime.now(), 'Pod', 'Ready'))
                    log.info('Pod %s in namespace %s is in Ready state',
                             event['object'].metadata.name, namespace)
            if set([i[0] for i in ready_time]) == set(names):
                log.info('All listed pods reporting Ready State')
                w.stop()
        return ready_time

    def _wait_for_controller_ready(self, kind, name, namespace, not_ready_first=True, timeout=0):
        """
        Waits for a Deployment or StatefulSet to be ready.

        :param kind: (str)['Deployment','StatefulSet']
        :param name: (str) Name of Deployment or StatefulSet
        :param namespace: (str) controller namespace
        :param not_ready_first: (bool) Wait for the controller to be in a not-ready state before waiting for ready.

        :return: (list) List of event tuples (<Pod_name>, <timestamp>, <kind>, <event>)
        """
        req_not_ready = False
        if not_ready_first:
            req_not_ready = True
        log.debug('Starting _wait_for_controller_ready for %s, %s, %s, not_ready_first=%s', kind, name, namespace, not_ready_first)
        if kind == 'Deployment':
            client = self._apps.list_namespaced_deployment
        elif kind == 'StatefulSet':
            client = self._apps.list_namespaced_stateful_set
        else:
            log.error("Invalid controller Kind, %s" % kind)
            return False

        w = kube_watch.Watch()
        had_not_rdy = False
        state_events = []
        for event in w.stream(client, namespace=namespace):  # , timeout=timeout):
            log.debug("WAIT CTRL READY Event: %s %s %s" % (event['type'], event['object'].kind, event['object'].metadata.name))
            if event['object'].metadata.name == name:
                if kind == 'Deployment':
                    cur_r = event['object'].status.replicas
                elif kind == 'StatefulSet':
                    cur_r = event['object'].status.current_replicas
                else:
                    cur_r = 0
                rea_r = event['object'].status.ready_replicas
                cnf_r = event['object'].spec.replicas
                log.debug('Replicas: %s, Current_Replicas: %s, Ready_Replicas: %s', cnf_r, cur_r, rea_r)
                if cur_r == rea_r == cnf_r:
                    if (had_not_rdy and req_not_ready) or (not req_not_ready):
                        log.debug('Full match, stopping watch')
                        # TODO: Send event to results handler.
                        state_events.append((name, datetime.datetime.now(), kind, 'Ready'))
                        log.info("%s %s in namespace %s transitioned into Ready state",
                                 kind, name, namespace)
                        w.stop()
                    else:
                        log.debug('WAIT CTRL READY: A Not-Ready status is required, but we have not seen it yet')
                else:
                    had_not_rdy = True
                    log.debug('WAIT CTRL READY: %s %s in namespace %s is not ready (%s/%s)' % (kind, name, namespace, rea_r, cnf_r))
                    state_events.append((name, datetime.datetime.now(), kind, 'NotReady(%s/%s)' % (rea_r, cnf_r)))
        return state_events

    def _identify_parent(self, obj):
        """
        _identify_parent

        Identifies the parent Deployment or StatefulSet of a Pod

        :param obj: (Pod) | (ReplicaSet)
        :return: (tuple) (<kind>, <name>)
        """
        owners = [(i.kind, i.name) for i in obj.metadata.ownerReferences]
        for owner in owners:
            if owner[0] in ['Deployment', 'StatefulSet']:
                log.debug('Owner for %s %s namespace %s is %s', obj.kind, obj.metadata.name, obj.metadata.namespace, owner)
                return owner
            elif owner[0] == 'ReplicaSet':
                replicaset_obj = self._resource_get(kind='ReplicaSet', name=owner[1], namespace=obj.metadata.namespace)
                return self._identify_parent(replicaset_obj)
        # No owner found
        return None, None

    def _build_not_uids(self, pods):
        """
        _build_not_uids

        Create a dict containing the UIDs of the pods to be deleted.  This is used to ensure that the pod wait_for_ready
        function waits for the NEW pods to be ready, and cannot be triggered by existing pods.

        :param pods: (list) List of Pod objects
        :return: (dict) A dict containing the UIDs
                {
                    <namespace> : {
                        <Pod Name> : <UID>
                    }
                }
        """
        not_uids = {}
        for pod in pods:
            if pod.metadata.namespace not in not_uids:
                not_uids[pod.metadata.namespace] = {}
            not_uids[pod.metadata.namespace][pod.metadata.name] = pod.metadata.uid
        return not_uids


    def delete_pods(self, pods, time_delete=False, time_replace=False, time_ctrl_ready=False):
        """
        delete_pods

        Deletes the specified pods, and returns a list of events that occured during the deletion.

        :param pods: (list) List of (<name>, <namespace>) tuples for the pods to be deleted
        :param time_delete: (bool) Wait for the pod to be deleted, and return a delete event with timestamp.
        :param time_replace: (bool) Wait for the replacement pod to become ready (only works for StatefulSets).
        :param time_ctrl_ready: (bool) Wait for the Controller to become ready.  If time_replace is specified for
                                       Deployment pods, time_ctrl_ready will be enabled automatically.

        :return: (list) List of event tuples (<Pod_name>, <timestamp>, <kind>, <event>)
        """
        log.debug('Attempting to delete pods %s ', pods)

        try:
            pods_to_delete = [self._resource_get('Pod', name=n, namespace=ns) for n,ns in pods]
        except Exception as e:
            log.error('Error occured trying to get pods')
            log.error(e)
            return False

        # Identify the UIDs of the running pods.  This allows detection of replacement pods for SatefulSets when
        # the pod name is the same as the deleted pod.
        orig_uids = {}
        for pod in pods_to_delete:
            if pod.metadata.namespace not in orig_uids:
                orig_uids[pod.metadata.namespace] = {}
            orig_uids[pod.metadata.namespace][pod.metadata.name] = pod.metadata.uid
        log.debug('Original UIDs: %s' % orig_uids)

        # Identify the controllers associated with the pods (input is only pod names, but we need to know
        # what controllers, and the controller type to properly detect replacement states.
        affected_controllers = set([(*self._identify_parent(p), p.metadata.namespace) for p in pods_to_delete])
        log.debug('Affected Controllers: %s', affected_controllers)

        # Build a list of pods that are part of a StatefulSet.  The state detection must be handled separately from
        # pods instantiated by a Deployment.
        statefulset_pods = [ p for p in pods_to_delete if self._identify_parent(p)[0] == 'StatefulSet']
        log.debug('StatefulSet Pods: %s', [(n.metadata.name,n.metadata.namespace) for n in statefulset_pods])

        # Build a list of pods that are part of a Deployment.
        deployment_pods = [ p for p in pods_to_delete if self._identify_parent(p)[0] == 'Deployment']
        log.debug('Deployment Pods: %s', [(n.metadata.name, n.metadata.namespace) for n in deployment_pods])

        # If we want to time the replacement for Deployment pods, this must be done using the
        # controller state, so force time_ctrl_ready to True.  Identifying direct replacements for deployment
        # pods is not feasible due to timing issues, especially when more than 1 pod is deleted at a time.
        if time_replace and len(deployment_pods) > 0:
            time_ctrl_ready = True

        # if timing the delete operation, start the watch before issuing delete command.

        # Note on the watches:  For some reason, even though the Kubernetes API supports it, the Python client
        # does not support watching of individual resources.  The watches must be started for a namespace scoped
        # resource type (i.e. only the <api>.list_namespaced_<resource> calls support watch.)  All resources of
        # that type will be reported by the watch, even ones that we are not interested in.  This makes the logic
        # in processing the received watch events more complicated (way too many IF statements), but I was unable
        # to find a way to narrow the watch, and simplify the logic through the Python API Client.
        # I could probably gather labels for the target resources, and filter each watch by labels, but I will leave
        # that for future enhancements (if needed).
        watch_futures = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=None) as ex:

            if time_delete:
                # A separate watch thread needs to be started for each namespace.
                namespaces = set([p.metadata.namespace for p in pods_to_delete ])
                for ns in namespaces:
                    ns_pod_names = [p.metadata.name for p in pods_to_delete if p.metadata.namespace == ns]
                    watch_futures[ex.submit(self._wait_for_pod_delete, ns_pod_names, ns)] = 'podDelete_%s' % ns

            if time_replace & (len(statefulset_pods) > 0):
                namespaces = set([p.metadata.namespace for p in statefulset_pods])
                for ns in namespaces:
                    ns_pod_names = [p.metadata.name for p in statefulset_pods if p.metadata.namespace == ns]
                    watch_futures[ex.submit(self._wait_for_pod_ready, ns_pod_names, ns, not_uids=orig_uids)] = 'podReady_%s' % ns

            if time_ctrl_ready:
                for ctlr in affected_controllers:
                    watch_futures[ex.submit(self._wait_for_controller_ready, *ctlr)] = 'ctlrReady_%s_%s_%s' % ctlr

            # Call _wait_for_controller_ready synchronously with not_ready_first=False to make sure
            # all the controllers affected are in a good state before we start deleting things.
            # (might want the ability to disable this)
            for ctlr in affected_controllers:
                self._wait_for_controller_ready(*ctlr, not_ready_first=False)

            del_thr = []
            del_events = []
            for pod in pods_to_delete:
                try:
                    del_thr.append(self._core.delete_namespaced_pod(name=pod.metadata.name, namespace=pod.metadata.namespace, async_req=True))
                    # TODO: This event needs to go to a results handler.
                    del_events.append((pod.metadata.name, datetime.datetime.now(), 'Pod', 'Delete_cmd'))
                except Exception as e:
                    log.error('Failed to delete Pod %s in namespace %s', pod.metadata.name, pod.metadata.namespace)
                    log.error(e)

            # There is nothing really useful in the returned objects from the delete command.
            # They are just the pod objects with metadata.deletion_timestamp set, but the timestamp is
            # offset by a calculated delay, so it is in the future, making it a "pod was deleted before this time"
            # timestamp, and not a representation of exactly when the pod was deleted.
            del_results = [thr.get() for thr in del_thr]
            if not len(del_results) == len(pods_to_delete):
                log.error('One or more pods failed to delete.')

        # collect the output from the futures (The events for now, until I have a results handler)
        # The even.result() function blocks until the thread terminates, the threads will terminate as soon as the
        # desired state is achieved.  This serves as both a "wait" and as a timestamp collection mechanism for
        # results reporting.
        all_events = []
        all_events += del_events
        for future in watch_futures:
            log.info('Collecting events for %s', watch_futures[future])
            all_events += future.result()
        log.info('Events: %s', all_events)
        return all_events

    def delete_pods_sync(self, pods, step=1, **kwargs):
        """
    `   delete_pods_sync

        Deletes the specified pods, one at a time.  this provides a simple free-running, synchronous delete of the
        selected pods.  Pods will be deleted in steps, and then wait for Ready state on the affected resources,
        before deleting the next set of pods.

        :param pods: (list) List of pod (<name>, <namespace>) tuples
        :param step: (int) Number of pods to delete at one time.
        :param kwargs:  kwargs from the delete_pods function
            time_delete=False, time_replace=False, time_ctrl_ready=False

        :return: (list) List of event tuples (<Pod_name>, <timestamp>, <kind>, <event>)
        """
        all_events = []
        while len(pods) > 0:
            del_pods = []
            while len(pods) > 0 and len(del_pods) < step:
                all_events += del_pods.append(pods.pop(0))
            self.delete_pods(del_pods, **kwargs)
        return all_events


# This doesnt really do much anymore.  It is more of a stepped delete so all the pods can be identified one time,
# but the delete happens in steps triggered by a function call rather than a state.  Basically, it is a non free-running
# stepped delete.
class CyclicDelete:
    """
    Class for performing a cyclic delete. Pods are deleted in batches.
    Pods from the list are deleted when 'delete_next()' is called.  Will delete
    every pod exactly 1 time.  If 'delete_next()' is called after all pods have been
    deleted, no action will be performed, and the function will return.

    Args:
        pod_list: a list of (name, namespace) tuples of pods that are to be deleted.
        pod_del: Instance of PodDelete Class.
        step: Number of pods to delete each time delete_next() is called
        kwargs: kwargs for the PodDelete.delete_pods() function

    Properties:
        pods_deleted_cnt: number of pods from the list that have been deleted.
        pods_remaining_cnt: number of pods still remaining to be deleted
        pods_remaining: list of pods remaining to be deleted
        pods_deleted: list of pods that were successfuly deleted
        results: list of events.

    Functions:
        delete_next(): Delete the next batch of pods in the pods_remaining list.
    """
    def __init__(self, pod_list, pod_del, step=1, **kwargs) -> None:
        self.pod_del = pod_del
        self.step = step
        self.delete_kwargs = kwargs
        self.pods_remaining = pod_list
        self.pods_deleted = []
        self.pods_in_progress = []
        self.results = []

    @property
    def pods_remaining_cnt(self):
        return len(self.pods_remaining)

    @property
    def pods_deleted_cnt(self):
        return len(self.pods_deleted)

    def delete_next(self):
        if len(self.pods_remaining) == 0:
            logging.error('No pods remaining to be delted')
            return
        while self.pods_remaining_cnt > 0 and len(self.pods_in_progress) < self.step:
            self.pods_in_progress.append(self.pods_remaining.pop())
        self.results += self.pod_del.delete_pods(self.pods_in_progress, **self.delete_kwargs)
        self.pods_deleted += self.pods_in_progress
        self.pods_in_progress = []


