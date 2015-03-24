#!/bin/bash
set -o errexit # Abort if one of our commands fail
set -o nounset

# An Orchestration Script to replace Deployments.
# Add this script on BeforeHosUp as a synchronous Script, and configure it
# using Global Variables or Script Parameters.
#
# NOTE: Script Parameters take precedence over Global Variables
# NOTE: You do NOT need to define Script Parameters if you are using Global
#       Variables
#
# Configuration:
# %deploy_path%, $DEPLOY_PATH        : The path to deploy to. Required.
# %git_repository%, $GIT_REPOSITORY  : The repository to clone. Required.
# %git_branch%, $GIT_BRANCH          : The branch to clone. Default: "master"
# $GIT_SSH_KEY                       : An (optional) unencrypted SSH Key.
#
# NOTE: Script Parameters can't be multiline, so SSH keys aren't supported as
# a Script Parameter

# Set up default environment variables
: ${DEPLOY_PATH:=""}
: ${GIT_REPOSITORY:=""}
: ${GIT_BRANCH:=master}
: ${GIT_SSH_KEY:=""}

# Use Global Variables for configuration not found in Script Parameters
: ${REAL_DEPLOY_PATH:="$DEPLOY_PATH"}
: ${REAL_GIT_REPOSITORY:="$GIT_REPOSITORY"}
: ${REAL_GIT_BRANCH:="$GIT_BRANCH"}
: ${REAL_GIT_SSH_KEY:="$GIT_SSH_KEY"}

# Check that required variables have indeed been submitted
[ -z "$REAL_DEPLOY_PATH" ]  && echo "ERROR: No deploy path was specified" && exit 1
[ -z "$REAL_GIT_REPOSITORY" ] && echo "ERROR: No repository was specified" && exit 1

# Install git if it's not already available
install_git () {
  if [ -f /etc/debian_version ]; then
    apt-get update
    apt-get install -y git
  elif [ -f /etc/redhat-release ]; then
    yum -y install git
  else
      echo "ERROR: Unsupported OS"
      exit 1
  fi
}
command -v git 2>&1 > /dev/null || install_git

# If a key was submitted, setup a wrapper file
if [ -n "$REAL_GIT_SSH_KEY" ]; then
  # Securely create the key and wrapper file
  # Ensure they are deleted on exit
  SSH_KEY_FILE="$(mktemp)"
  SSH_WRAPPER_FILE="$(mktemp)"
  trap "rm -f '$SSH_KEY_FILE' '$SSH_WRAPPER_FILE'" EXIT
  chmod 700 "$SSH_WRAPPER_FILE"

  # Setup the contents of those files
  echo "$REAL_GIT_SSH_KEY" > $SSH_KEY_FILE
  echo "#!/bin/sh" > $SSH_WRAPPER_FILE
  echo "exec ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i '$SSH_KEY_FILE' \"\$@\"" >> $SSH_WRAPPER_FILE

  # Pass the wrapper file to git via the GIT_SSH environment variable
  export GIT_SSH=$SSH_WRAPPER_FILE
fi

# Do the deployment
if [ ! -d "$REAL_DEPLOY_PATH" ]; then
  # If the code wasn't deployed yet, ensure that the tree to it exists
  mkdir -p $REAL_DEPLOY_PATH
  rm -r $REAL_DEPLOY_PATH

  # Then deploy the code
  git clone --branch $REAL_GIT_BRANCH $REAL_GIT_REPOSITORY $REAL_DEPLOY_PATH
else
  # If the code was already deployed, update it.
  cd $REAL_DEPLOY_PATH
  git pull
  git checkout $REAL_GIT_BRANCH
fi
