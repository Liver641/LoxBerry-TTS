<?php
/**
* Submodul: bidirectonal Interface
*
**/


/**
/* Funktion : receive_post_request --> Function to receive and validate incoming Requests
/* @param: 	empty
/*
/* @return: array (
/*			[0] Text for T2S (string)
/*			[1] greet=0 w/o greeting, greet=1 with greeting (bolean)
/**/

function process_post_request() {
	
	#$level = LBSystem::pluginloglevel();
	
	// http://thisinterestsme.com/receiving-json-post-data-via-php/
	// http://thisinterestsme.com/sending-json-via-post-php/
	global $text, $decoded, $time_start, $level;
	
	print_r('');
	if ($level == 7) {
		print '***********************************************************************<br>';
		print ' Details of incoming http Request<br>';
		print '***********************************************************************<br>';
		print '<br>';
	}
	// Make sure that it is a POST request.
	if(strcasecmp($_SERVER['REQUEST_METHOD'], 'POST') != 0){
		LOGERR("T2S Interface ** Request method must be POST!");
		if ($level == 7) {
			print "Error: T2S Interface ** Request method must be POST!<br>";
		}
		exit;
	}
	if ($level == 7) {
		print "Success: T2S Interface ** Request method is POST!<br>";
	}
	// Make sure that the content type of the POST request has been set to application/json
	$contentType = isset($_SERVER["CONTENT_TYPE"]) ? trim($_SERVER["CONTENT_TYPE"]) : '';
	if(strcasecmp($contentType, 'application/json') != 0){
		LOGERR("T2S Interface ** Content type must be: application/json");
		if ($level == 7) {
			print "Error: T2S Interface ** Content type must be: application/json!<br>";
		}
		exit;
	}
	if ($level == 7) {
		print "Success: T2S Interface ** Content type is: application/json!<br>";
	}
	
	// Receive the RAW post data.
	$content = trim(file_get_contents("php://input"));
	
	// Attempt to decode the incoming RAW post data from JSON.
	$decoded = json_decode($content, true);
	
	// If json_decode failed, the JSON is invalid.
	if(!is_array($decoded)){
		LOGERR("T2S Interface ** Received content contained invalid JSON!");
		if ($level == 7) {
			print "Error: T2S Interface ** Received content contained invalid JSON!<br>";
		}
		exit;
	}
	if ($level == 7) {
		print "Success: T2S Interface ** Received content contained valid JSON!<br>";
	}
	LOGOK("T2S Interface ** POST request has been successful processed!");
	if ($level == 7) {
		print "Success: T2S Interface ** POST request has been successful processed!<br>";
		print '<br>';
	}
	
	if ($level == 7) {
		print '***********************************************************************<br>';
		print ' Data Import from incoming http Request (Array)<br>';
		print '***********************************************************************<br>';
		print '<br>';
		print_r($decoded);
		print '<br>';
	}
	return ($decoded);
}



/**
/* Funktion : jsonfile --> Erstellt ein JSON file mit den notwenigen Infos
/* @param: 	leer
/*
/* @return: JSON file für weitere Verwendung
/**/	

function jsonfile($filename)  {
	global $volume, $config, $MP3path, $messageid, $level, $time_start, $filename, $infopath, $myFolder, $fullfilename, $config, $ttsinfopath, $filepath, $ttspath, $myIP, $plugindatapath, $lbhomedir, $files, $psubfolder, $hostname, $fullfilename, $text, $textstring, $duration;
	
	$filenamebatch = $config['SYSTEM']['interfacepath']."/".$fullfilename;
	$ttspath = $config['SYSTEM']['ttspath'];
	$filepath = $config['SYSTEM']['mp3path'];
	$ttsinfopath = $config['SYSTEM']['interfacepath']."/";
	
	
	// ** get details of MP3
	// https://github.com/JamesHeinrich/getID3/archive/master.zip
	require_once("bin/getid3/getid3.php");
    $MP3filename = $ttspath."/".$messageid.".mp3";
	$getID3 = new getID3;
    $file = $getID3->analyze($MP3filename);
	$duration = round($file['playtime_seconds'] * 1000, 0);
	$bitrate = $file['bitrate'];
	$sample_rate = $file['mpeg']['audio']['sample_rate'];
    	
	LOGGING("filename of MP3 file: '".$filename."'", 5);
	# prüft ob Verzeichnis für Übergabe existiert
	$is_there = file_exists($ttsinfopath);
	if ($is_there === false)  {
		LOGGING("The interface folder seems not to be available!! System now try to create the 'share' folder", 4);
		mkdir($ttsinfopath);
		LOGGING("Folder '".$ttsinfopath."' has been succesful created.", 5);
	} else {
		LOGGING("Folder '".$infopath."' to pass over audio infos is already there (".$ttsinfopath.")", 5);
	}
	# Löschen alle vorhandenen Dateien aus dem info folder
	chdir($ttsinfopath);
	foreach (glob("*.*") as $file) {
		LOGGING("File: '".$file."' has been deleted from '".$infopath."' folder",5);
		#unlink($file);
	}
		$files = array(
						'full-ttspath' => $config['SYSTEM']['ttspath']."/".$filename.".mp3",
						'path' => $config['SYSTEM']['path']."/",
						'full-cifsinterface' => $config['SYSTEM']['cifsinterface']."/".$filename.".mp3",
						'cifsinterface' => $config['SYSTEM']['cifsinterface']."/",
						'full-httpinterface' => $config['SYSTEM']['httpinterface']."/".$filename.".mp3",
						#'sonosinterface' => $config['SYSTEM']['sonosinterface']."/".$filename.".mp3",
						'httpinterface' => $config['SYSTEM']['httpinterface']."/",
						'mp3-filename-MD5' => $filename,
						'duration-ms' => $duration,
						'bitrate' => $bitrate,
						'sample-rate' => $sample_rate,
						'text' => $textstring
						);
	if ($level == 7) {
		print '***********************************************************************<br>';
		print ' Return Source Data post T2S processing (Array)<br>';
		print '***********************************************************************<br>';
		print '<br>';
		print_r($files);
		print '<br>';
		print '**********************************************************************************************<br>';
		print ' Return Source Data post T2S processing (JSON)<br>';
		print " saved in: '".$config['SYSTEM']['path']."/interface/".$fullfilename."'<br>";
		print '**********************************************************************************************<br>';
		print '<br>';
		$json = json_encode($files);
		print_r($json);
	}
	try {
		File_Put_Array_As_JSON($filenamebatch, $files, $zip=false);
		LOGGING("Information of processed T2S has been added to JSON file", 7);
	} catch (Exception $e) {
		LOGGING("JSON file could not be saved! Please check your system (permission, credentials, etc.)", 3);
		exit;
	}
	LOGGING("MP3 file has been saved successful at '".$files['path']."'.", 6);
	LOGGING("file '".$fullfilename."' has been successful saved in 'interface' folder", 5);
	#get_results();
	return $files;
	
}


function get_results() {
	 
	global $myIP, $files, $json;
	
	// API Url
	$url = 'http://'.$myIP.'/plugins/sonos4lox_tts/index.php';
	
	// Initiate cURL.
	$ch = curl_init($url);
	 
	// Encode the array into JSON.
	$jsonDataEncoded = json_encode($files);
		 
	// Tell cURL that we want to send a POST request.
	curl_setopt($ch, CURLOPT_POST, 1);
	 
	// Attach our encoded JSON string to the POST fields.
	curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonDataEncoded);
	 
	// Set the content type to application/json
	curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json')); 
		 
	// Execute the request
	$result = curl_exec($ch);

	// was the request successful?
	if($result === false)  {
		print "Der POST Request war nicht erfolgreich!";
		echo'<br>';
		echo'<br>';
	} else {
		print "Der POST Request war erfolgreich!";
		echo'<br>';
		echo'<br>';
	}
	// close cURL
	curl_close($ch);
}


	


?>