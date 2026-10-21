<?php
header('Content-Type: text/plain');
header('X-Lab-Worker-Pid: ' . getmypid());
echo "HEALTHY ", PHP_VERSION, " ", PHP_SAPI, "\n";
