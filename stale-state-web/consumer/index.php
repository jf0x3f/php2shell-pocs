<?php
header('Content-Type: text/plain');
header('X-Lab-Worker-Pid: ' . getmypid());
echo "CONSUMER_REACHED ", PHP_VERSION, " ", PHP_SAPI, " auto_detect_line_endings=", ini_get('auto_detect_line_endings'), "\n";
