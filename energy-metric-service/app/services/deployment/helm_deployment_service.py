"""
Helm Deployment Service
Handles deployment of Helm charts
"""

import logging
import asyncio
import tempfile
import os
from datetime import datetime
from typing import Dict, Any
import yaml

logger = logging.getLogger(__name__)


class HelmDeploymentService:
    """Service to handle deployment of Helm charts."""

    def __init__(self):
        pass

    async def deploy_helm_chart(
        self,
        manifest: str,
        namespace: str = "default",
        custom_labels: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Deploy a Helm chart to the cluster.

        The manifest should contain Helm chart definition including:
        - Chart metadata (name, version, etc.)
        - Values to override

        Args:
            manifest: YAML manifest containing Helm chart definition and values
            namespace: Target namespace
            custom_labels: Optional custom labels to add (via Helm values)

        Returns:
            Dict with deployment result
        """
        try:
            # Parse the manifest to extract chart info and values
            try:
                helm_config = yaml.safe_load(manifest)
            except yaml.YAMLError as e:
                logger.error(f"Invalid Helm configuration YAML: {e}")
                return {
                    "success": False,
                    "error": f"Invalid Helm configuration YAML: {str(e)}",
                    "status": "failed"
                }

            # Extract Helm chart information
            chart_name = helm_config.get('chart', {}).get('name')
            chart_version = helm_config.get('chart', {}).get('version')
            chart_repo = helm_config.get('chart', {}).get('repository')
            release_name = helm_config.get('releaseName', chart_name)
            values = helm_config.get('values', {})

            if not chart_name:
                logger.error("Helm chart name not specified in manifest")
                return {
                    "success": False,
                    "error": "Helm chart name not specified in manifest",
                    "status": "failed"
                }

            logger.info(f"Deploying Helm chart '{chart_name}' as release '{release_name}' in namespace '{namespace}'")

            # Inject custom labels into values if provided
            if custom_labels:
                if 'labels' not in values:
                    values['labels'] = {}
                values['labels'].update(custom_labels)

            # Create temporary values file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as values_file:
                yaml.dump(values, values_file)
                values_file_path = values_file.name

            try:
                # Add Helm repository if specified
                if chart_repo:
                    await self._add_helm_repo(chart_repo)

                # Install or upgrade Helm chart
                result = await self._helm_install_or_upgrade(
                    release_name=release_name,
                    chart_name=chart_name,
                    chart_version=chart_version,
                    namespace=namespace,
                    values_file_path=values_file_path
                )

                return result

            finally:
                # Cleanup temporary values file
                try:
                    os.unlink(values_file_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary values file: {e}")

        except Exception as e:
            logger.error(f"Helm deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }

    async def _add_helm_repo(self, repo_config: Dict[str, str]) -> None:
        """
        Add Helm repository.

        Args:
            repo_config: Dictionary with 'name' and 'url' keys
        """
        try:
            repo_name = repo_config.get('name')
            repo_url = repo_config.get('url')

            if not repo_name or not repo_url:
                logger.warning("Helm repository name or URL not specified, skipping repo add")
                return

            logger.info(f"Adding Helm repository '{repo_name}' from '{repo_url}'")

            # Add Helm repo
            process = await asyncio.create_subprocess_exec(
                'helm', 'repo', 'add', repo_name, repo_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.warning(f"Failed to add Helm repo (may already exist): {stderr.decode()}")
            else:
                logger.info(f"Successfully added Helm repository '{repo_name}'")

            # Update Helm repositories
            logger.info("Updating Helm repositories...")
            process = await asyncio.create_subprocess_exec(
                'helm', 'repo', 'update',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("Successfully updated Helm repositories")
            else:
                logger.warning(f"Failed to update Helm repositories: {stderr.decode()}")

        except Exception as e:
            logger.warning(f"Error adding Helm repository: {e}")

    async def _helm_install_or_upgrade(
        self,
        release_name: str,
        chart_name: str,
        chart_version: str = None,
        namespace: str = "default",
        values_file_path: str = None
    ) -> Dict[str, Any]:
        """
        Install or upgrade a Helm release.

        Args:
            release_name: Name of the Helm release
            chart_name: Name of the Helm chart
            chart_version: Version of the chart (optional)
            namespace: Target namespace
            values_file_path: Path to values file

        Returns:
            Dict with deployment result
        """
        try:
            # Build Helm command
            helm_cmd = [
                'helm', 'upgrade', '--install',
                release_name, chart_name,
                '--namespace', namespace,
                '--create-namespace'
            ]

            # Add version if specified
            if chart_version:
                helm_cmd.extend(['--version', chart_version])

            # Add values file if provided
            if values_file_path:
                helm_cmd.extend(['--values', values_file_path])

            logger.info(f"Executing Helm command: {' '.join(helm_cmd)}")

            # Execute Helm command
            process = await asyncio.create_subprocess_exec(
                *helm_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Successfully deployed Helm release '{release_name}'")
                return {
                    "success": True,
                    "release_name": release_name,
                    "chart_name": chart_name,
                    "namespace": namespace,
                    "deployed_at": datetime.utcnow().isoformat(),
                    "status": "deployed",
                    "output": stdout.decode()
                }
            else:
                error_msg = stderr.decode()
                logger.error(f"Helm deployment failed for release '{release_name}': {error_msg}")
                return {
                    "success": False,
                    "error": f"Helm deployment failed: {error_msg}",
                    "status": "failed"
                }

        except FileNotFoundError:
            error_msg = "Helm CLI not found. Please ensure Helm is installed and available in PATH."
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "status": "failed"
            }
        except Exception as e:
            logger.error(f"Error executing Helm command: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }

    async def uninstall_helm_release(
        self,
        release_name: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Uninstall a Helm release.

        Args:
            release_name: Name of the Helm release to uninstall
            namespace: Namespace of the release

        Returns:
            Dict with uninstall result
        """
        try:
            logger.info(f"Uninstalling Helm release '{release_name}' from namespace '{namespace}'")

            # Execute Helm uninstall command
            process = await asyncio.create_subprocess_exec(
                'helm', 'uninstall', release_name,
                '--namespace', namespace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Successfully uninstalled Helm release '{release_name}'")
                return {
                    "success": True,
                    "release_name": release_name,
                    "namespace": namespace,
                    "status": "uninstalled"
                }
            else:
                error_msg = stderr.decode()
                logger.error(f"Failed to uninstall Helm release '{release_name}': {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status": "failed"
                }

        except Exception as e:
            logger.error(f"Error uninstalling Helm release: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }

    async def get_helm_release_status(
        self,
        release_name: str,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Get the status of a Helm release.

        Args:
            release_name: Name of the Helm release
            namespace: Namespace of the release

        Returns:
            Dict with release status
        """
        try:
            # Execute Helm status command
            process = await asyncio.create_subprocess_exec(
                'helm', 'status', release_name,
                '--namespace', namespace,
                '--output', 'json',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                import json
                status_data = json.loads(stdout.decode())
                return {
                    "success": True,
                    "release_name": release_name,
                    "status": status_data.get('info', {}).get('status'),
                    "data": status_data
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode(),
                    "status": "not_found"
                }

        except Exception as e:
            logger.error(f"Error getting Helm release status: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "error"
            }
