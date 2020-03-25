#!/bin/sh -e

cmdname="$(basename "$0")"

usage() {
    cat << USAGE >&2
Usage:
    $cmdname

    Docker deployment script for web target
    Pull the latest docker image and recreate relevant containers

USAGE
    exit 1
}


echo "📦 Updating images..."
docker-compose pull

echo "🚀 Deploying containers..."
docker-compose up --detach
