#
# Copyright (c) 2020 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#
from logging import Logger

from kubernetes.client import AppsV1Api, CoreV1Api

from cloudsure.providers.nfv.k8s.client_initializer import ClientInitializer
from cloudsure.tpkg_core.user_script.error import UserScriptFrameworkError


class K8sClientV1():
    """ User-script kubernetes client.

    This class is intended to be used to access a Kubernetes cluster through REST APIs. The REST API access is
    provided by the standard `kubernetes client <https://github.com/kubernetes-client/python/>`_. The class accepts
    authentication parameters so that once an instance has been initialized, authentication with the cluster will
    have already been established.
    """
    def __init__(self, log: Logger, vim_profile: dict) -> None:
        """ Constructor.

        :param Logger log: A default logger for the class. Note: This logger would only really be used in this
            class instance since the VimBase class creates its own loader.
        :param dict vim_profile: A dict containing the Kubernetes VIM profile. The function ensures that the VIM
            profile is for Kubernetes and uses the authentication values provided in the profile to authenticate
            with the target Kubernetes cluster.
        :raises UserScriptFrameworkError: If an error occurs during the initialization of the object.
        """
        self._log = log

        try:
            # This injectable is only available for kubernetes access
            provider = vim_profile['provider']
            if provider['type'] != 'KUBERNETES':
                raise Exception('')

            # Initialize and authorize an object to be used to access the kubernetes API
            self._k8s = ClientInitializer(provider['authentication'])
        except Exception as e:
            raise UserScriptFrameworkError(f'Unable to initialize a VIM driver: {e}') from e

    @property
    def api_end_point(self) -> str:
        """
        Reports the Kubernetes API end-point URL.

        :return: Kubernetes API end-point URL.
        """
        return self._k8s.api_end_point

    @property
    def v1_core_api(self) -> CoreV1Api:
        """ Reports the core API object.

        :return: Core API object.
        """
        return self._k8s.v1_core_api

    @property
    def v1_app_api(self) -> AppsV1Api:
        """ Reports the APP API object.

        :return: APP API object.
        """
        return self._k8s.v1_app_api

 @property
    def v1_app_api(self) -> AppsV1Api:
        """ Reports the APP API object.

        :return: APP API object.
        """
        return self._k8s.v1_app_api

    @property
    def v1_autoscale_api(self) -> AutoscaleV1Api:
        """
        Reports the Autoscale v1 API object.

        :return: Autoscale v1 API object.
        """
        return self._k8s._v1_autoscale_api

   @property
    def v2_autoscale_api(self) -> AutoscaleV2Api:
        """
        Reports the Autoscale v2 API object.

        :return: Autoscale v2 API object.
        """
        return self._k8s._v2_autoscale_api

  @property
    def v2beta1_autoscale_api(self) -> AutoscalingV2beta1Api:
        """
        Reports the Autoscale v2beta1 API object.

        :return: Autoscale v2beta1 API object.
        """
        return self._k8s._v2beta1_autoscale_api

  @property
    def v2beta2_autoscale_api(self) -> AutoscalingV2beta2Api:
        """
        Reports the Autoscale v2beta2 API object.

        :return: Autoscale v2beta2 API object.
        """
        return self._k8s._v2beta2_autoscale_api

  @property
    def networking_api(self) -> NetworkingApi:
        """
        Reports the Networking API object.

        :return: Networking API object.
        """
        return self._k8s._networking_api

  @property
    def v1_networking_api(self) -> NetworkingV1Api:
        """
        Reports the Networking V1 API object.

        :return: Networking V1 API object.
        """
        return self._k8s._v1_networking_api

  @property
    def v1_policy_api(self) -> PolicyV1Api:
        """
        Reports the Policy API object.

        :return: Policy API object.
        """
        return self._k8s._v1_policy_api

  @property
    def scheduling_api(self) -> SchedulingApi:
        """
        Reports the Scheduling API object.

        :return: Scheduling API object.
        """
        return self._k8s._scheduling_api

  @property
    def v1_scheduling_api(self) -> SchedulingV1Api:
        """
        Reports the Scheduling v1 API object.

        :return: Scheduling v1 API object.
        """
        return self._k8s._v1_scheduling_api

  @property
    def storage_api(self) -> StorageApi:
        """
        Reports the Storage API object.

        :return: Storage API object.
        """
        return self._k8s._storage_api

  @property
    def v1_storage_api(self) -> StorageV1Api:
        """
        Reports the Storage v1 API object.

        :return: Storage v1 API object.
        """
        return self._k8s._v1_storage_api

  @property
    def custom_objects_api(self) -> CustomObjectsApi:
        """
        Reports the Custom API object.

        :return: Custom API object.
        """
        return self._k8s._custom_objects_api
