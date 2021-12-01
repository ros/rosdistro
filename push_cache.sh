#!/bin/bash

# Parameters
token=$1
file=$2
file_name=$(basename ${file})
user="cmrobotics"
repo="rosdistro"
address_get_latest="https://api.github.com/repos/${user}/${repo}/releases/latest"

# Get the latest release id
res=$(curl -H "Authorization: token ${token}" -H "Accept: application/vnd.github.v3+json" -s ${address_get_latest})
release_id=$(echo ${res} | python -c '
import json,sys;
print(json.load(sys.stdin)["id"])
')

# Get the asset id of the file for the latest release in case it exists
asset_id=$(echo ${res} | python -c "
import json,sys;
ret = json.load(sys.stdin);
file_asset = next((item for item in ret[\"assets\"] if item[\"name\"] == \"${file_name}\"), {\"id\": \"\"});
print(file_asset[\"id\"])
")

# Use the API to update the asset if the file already exists
# Otherwise, use the API to create the asset
if [ -n "${asset_id}" ]; then
  address_push_file="https://api.github.com/repos/${user}/${repo}/releases/assets/${asset_id}"
  status_code=$(curl -sL -o /dev/null -w '%{http_code}' -X DELETE \
    -H "Authorization: token ${token}" \
    -H "Accept: application/vnd.github.v3+json" \
    ${address_push_file})

  if [ $status_code = 204 ]; then
    echo "SUCCESS: Asset deleted. Will try to upload next."
  else
    echo "ERROR: Could not delete the file (status code: ${status_code}), aborting since I will not be able to upload!"
    exit 1
  fi
fi

address_push_file="https://uploads.github.com/repos/${user}/${repo}/releases/${release_id}/assets?name=${file_name}"
status_code=$(curl -sL -o /dev/null -w '%{http_code}' -X POST \
  -H "Authorization: token ${token}" \
  -H "Content-Type: $(file -b --mime-type ${file})" \
  -H "Accept: application/vnd.github.v3+json" \
  --data-binary @${file} \
  ${address_push_file})

if [ $status_code = 201 ]; then
  echo "SUCCESS: Asset \"${file_name}\" successfully uploaded to GitHub Release!"
else
  echo "ERROR: Something went wrong (status code: ${status_code}), aborting!"
  exit 1
fi
