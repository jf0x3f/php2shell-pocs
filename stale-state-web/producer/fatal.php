<?php
header('Content-Type: text/plain');
header('X-Lab-Worker-Pid: ' . getmypid());
trigger_error('LOCAL_CVE_109619_PRODUCER_FATAL', E_USER_ERROR);
