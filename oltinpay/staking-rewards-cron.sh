#!/bin/bash
# Daily staking rewards calculation
# Run at midnight UTC

curl -s -X POST http://oltinpay-api:8000/api/v1/staking/rewards/calculate >> /var/log/staking-rewards.log 2>&1
echo " - Sun Jan 25 16:33:59 CET 2026" >> /var/log/staking-rewards.log
