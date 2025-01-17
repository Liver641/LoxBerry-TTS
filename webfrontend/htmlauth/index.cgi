#!/usr/bin/perl -w

# Copyright 2018 Oliver Lewald, olewald64@gmail.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################

use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use LoxBerry::Storage;
use LoxBerry::JSON;

use warnings;
use strict;
use File::Copy;
use Config::Simple '-strict';

#use CGI::Carp qw(fatalsToBrowser);
#use CGI qw/:standard/;
#use LWP::Simple;
#use LWP::UserAgent;
#use File::HomeDir;
#use Cwd 'abs_path';
#use JSON qw( decode_json );
#use utf8;
use Data::Dumper;

##########################################################################
# Generic exception handler
##########################################################################

# Every non-handled exceptions sets the @reason variable that can
# be written to the logfile in the END function

$SIG{__DIE__} = sub { our @reason = @_ };

##########################################################################
# Variables
##########################################################################

my $namef;
my $value;
my %query;
my $template_title;
my $error;
my $saveformdata = 0;
my $do = "form";
my $helplink;
my $helptemplate;
my $storepath;
my $fullpath;
my $i;
my $template;
our $lbpbindir;
my %SL;

my $helptemplatefilename		= "help.html";
my $languagefile 				= "tts_all.ini";
my $maintemplatefilename	 	= "index.html";
my $successtemplatefilename 	= "success.html";
my $errortemplatefilename 		= "error.html";
my $noticetemplatefilename 		= "notice.html";
my $no_error_template_message	= "The error template is not readable. We must abort here. Please try to reinstall the plugin.";
my $pluginconfigfile 			= "tts_all.cfg";
my $outputfile 					= 'output.cfg';
my $outputusbfile 				= 'hats.json';
my $pluginlogfile				= "text2speech.log";
my $devicefile					= "/tmp/soundcards2.txt";
my $lbhostname 					= lbhostname();
my $lbip 						= LoxBerry::System::get_localip();
#my $interfacefolder			= "interface";
my $ttsfolder					= "tts";
my $mp3folder					= "mp3";
my $azureregion					= "westeurope"; # Change here if you have a Azure API key for diff. region
#my $ttsinfo					= "info";
#my $urlfile					= "https://raw.githubusercontent.com/Liver64/LoxBerry-Sonos/master/webfrontend/html/release/info.txt";
my $log 						= LoxBerry::Log->new ( 
								name => 'Webinterface', 
								#filename => $lbplogdir ."/". $pluginlogfile, 
								#append => 1, 
								addtime => 1
								);
my $helplink 					= "https://www.loxwiki.eu/x/uoFYAg";
my $pcfg 						= new Config::Simple($lbpconfigdir . "/" . $pluginconfigfile);
my %Config 						= $pcfg->vars() if ( $pcfg );
our $error_message				= "";

# Set new config options for upgrade installations
# cachsize
if (!defined $pcfg->param("MP3.cachesize")) {
	$pcfg->param("MP3.cachesize", "100");
}
# add new parameter for Azure TTS"
if (!defined $pcfg->param("TTS.regionms"))  {
	$pcfg->param("TTS.regionms", $azureregion);
	$pcfg->save() or &error;
}
# splitsentence
if (!defined $pcfg->param("MP3.splitsentences")) {
	$pcfg->param("MP3.splitsentences", "");
	$pcfg->save() or &error;
}
# USB device No.
if (!defined $pcfg->param("SYSTEM.usbdevice")) {
	$pcfg->param("SYSTEM.usbdevice", 0);
	$pcfg->save() or &error;
}# USB card No.
if (!defined $pcfg->param("SYSTEM.usbcardno")) {
	$pcfg->param("SYSTEM.usbcardno", 1);
	$pcfg->save() or &error;
}



##########################################################################
# Read Settings
##########################################################################

# read language
my $lblang = lblanguage();
#my %SL = LoxBerry::System::readlanguage($template, $languagefile);

# Read Plugin Version
my $sversion = LoxBerry::System::pluginversion();

# read all POST-Parameter in namespace "R".
my $cgi = CGI->new;
$cgi->import_names('R');

LOGSTART "T2S UI started";

##########################################################################

# deletes the log file
if ( $R::delete_log )
{
	print "Content-Type: text/plain\n\nOK - In this version, this call does nothing";
	exit;
}

#########################################################################
# Parameter
#########################################################################

$saveformdata = defined $R::saveformdata ? $R::saveformdata : undef;
$do = defined $R::do ? $R::do : "form";

##########################################################################
# Init Main Template
##########################################################################
inittemplate();

##########################################################################
# Set LoxBerry SDK to debug in plugin is in debug
##########################################################################

if($log->loglevel() eq "7") {
	$LoxBerry::System::DEBUG 	= 1;
	$LoxBerry::Web::DEBUG 		= 1;
	$LoxBerry::Storage::DEBUG	= 1;
	$LoxBerry::Log::DEBUG		= 1;
}

##########################################################################
# Language Settings
##########################################################################

$template->param("LBHOSTNAME", lbhostname());
$template->param("LBLANG", $lblang);
$template->param("SELFURL", $ENV{REQUEST_URI});
$template->param("LBPPLUGINDIR", $lbpplugindir);

LOGDEB "Read main settings from " . $languagefile . " for language: " . $lblang;

# übergibt Plugin Verzeichnis an HTML
$template->param("PLUGINDIR" => $lbpplugindir);

# übergibt Data Verzeichnis an HTML
#$template->param("DATADIR" => $lbpdatadir);

# übergibt Log Verzeichnis und Dateiname an HTML
$template->param("LOGFILE" , $lbplogdir . "/" . $pluginlogfile);

##########################################################################
# check if config files exist and they are readable
##########################################################################

# Check if tts_all.cfg file exist/directory exists
if (!-r $lbpconfigdir . "/" . $pluginconfigfile) 
{
	LOGWARN "Plugin config file/directory does not exist";
	LOGDEB "Check if config directory exists. If not, try to create it.";
	$error_message = $SL{'ERRORS.ERR_CREATE_CONFIG_DIRECTORY'};
	mkdir $lbpconfigdir unless -d $lbpconfigdir or &error; 
	LOGOK "Config directory: " . $lbpconfigdir . " has been created";
}

##########################################################################
# Main program
##########################################################################

our %navbar;
$navbar{1}{Name} = "$SL{'T2S.MENU_SETTINGS'}";
$navbar{1}{URL} = './index.cgi';
# $navbar{2}{Name} = "Examples and testing";
# $navbar{2}{URL} = 't2sexamples.cgi';
$navbar{3}{Name} = "$SL{'T2S.MENU_WIZARD'}";
$navbar{3}{URL} = './index.cgi?do=wizard';
$navbar{99}{Name} = "$SL{'T2S.MENU_LOGFILES'}";
$navbar{99}{URL} = './index.cgi?do=logfiles';

if ($R::saveformdata) {
  &save;

} 

if(!defined $R::do or $R::do eq "form") {
	$navbar{1}{active} = 1;
	$template->param("FORM", "1");
	&form;
} elsif ($R::do eq "wizard") {
	LOGTITLE "Show logfiles";
	$navbar{3}{active} = 1;
	$template->param("WIZARD", "1");
	printtemplate();
} elsif ($R::do eq "logfiles") {
	LOGTITLE "Show logfiles";
	$navbar{99}{active} = 1;
	$template->param("LOGFILES", "1");
	$template->param("LOGLIST_HTML", LoxBerry::Web::loglist_html());
	printtemplate();
}

$error_message = "Invalid do parameter";
error();

exit;


#####################################################
# Form-Sub
#####################################################

sub form {


	LOGTITLE "Display form";
	
	my $storage = LoxBerry::Storage::get_storage_html(
					formid => 'STORAGEPATH', 
					currentpath => $pcfg->param("SYSTEM.path"),
					custom_folder => 1,
					type_all => 1, 
					readwriteonly => 1, 
					data_mini => 1,
					label => "$SL{'T2S.SAFE_DETAILS'}");
					
	$template->param("STORAGEPATH", $storage);
	
	# fill saved values into form
	$template		->param("SELFURL", $ENV{REQUEST_URI});
	$template		->param("T2S_ENGINE" 	=> $pcfg->param("TTS.t2s_engine"));
	$template		->param("VOICE" 		=> $pcfg->param("TTS.voice"));
	$template		->param("CODE" 			=> $pcfg->param("TTS.messageLang"));
	$template		->param("VOLUME" 		=> $pcfg->param("TTS.volume"));
	$template		->param("DATADIR" 		=> $pcfg->param("SYSTEM.path"));
	
	# Get current storage folder
	$storepath = $pcfg->param("SYSTEM.path"),
		
	# Full path to check if folders already there
	#$fullpath = $storepath."/".$lbhostname."/".$ttsfolder."/".$mp3folder;
	
	# Split path
	#my @fields = split /\//, $storepath;
	#my $folder = $fields[3];
	
	#if ($folder ne "data")  {	
	#	if(-d $fullpath)  {
	#		LOGDEB "Folders already exists.";
	#	} else {
	#		# Create folder
	#		require File::Path;
	#		File::Path::make_path($fullpath, { chmod => 0777 } );
	#		LOGDEB "Directory '".$storepath."/".$lbhostname."/".$ttsfolder."/".$mp3folder."' has been created.";
			
	# Copy delivered MP3 files from local dir (source) to new created folder
	# my $source_dir = $lbpdatadir.'/mp3';
	#my $target_dir = $fullpath;

	#opendir(my $DIRE, $source_dir) || die "Can't opendir $source_dir: $!";  
	#my @files = readdir($DIRE);

	#foreach my $t (@files)	{
	#   if(-f "$source_dir/$t" )  {
	#	  #Check with -f only for files (no directories)
	#	  copy "$source_dir/$t", "$target_dir/$t";
	#   }
	#}
	#closedir($DIRE);
	#LOGINF "All MP3 files has been copied successful to target location.";
	#}
	#} else {
	#LOGINF "Local directory has been selected.";
	#}
	
	# Load saved values for "select"
	my $t2s_engine	= $pcfg->param("TTS.t2s_engine");
	
	# fill dropdown with list of files from mp3 folder
	my $dir = $lbpdatadir.'/mp3/';
	my $mp3_list;
	
    opendir(DIR, $dir) or die $!;
	my @dots 
        = grep { 
            /\.mp3$/      # just files ending with .mp3
	    && -f "$dir/$_"   # and are files
	} 
	readdir(DIR);
	my @sorted_dots = sort { $a <=> $b } @dots;		# sort files numericly
    # Loop through the array adding filenames to dropdown
    foreach my $file (@sorted_dots) {
		$mp3_list.= "<option value='$file'>" . $file . "</option>\n";
    }
	closedir(DIR);
	$template->param("MP3_LIST", $mp3_list);
	LOGDEB "List of MP3 files has been successful loaded";
	LOGOK "Plugin has been successfully loaded.";
	
	my $line;
	my $out_list;
	
	# Fill output Dropdown
	my $outpath = $lbpconfigdir . "/" . $outputfile;
	open my $in, $outpath or die "$outpath: $!";
	
	my $i = 1;
	while ($line = <$in>) {
		if ($i < 10) {
			$out_list.= "<option value='00".$i++."'>" . $line . "</option>\n";
		} else {
			$out_list.= "<option value='0".$i++."'>" . $line . "</option>\n";
		}
	}
	close $in;
	$template->param("OUT_LIST", $out_list);
	
	
	# Fill USB output Dropdown
	my $usb_list;
	my $jsonparser = LoxBerry::JSON->new();
	my $config = $jsonparser->open(filename => $lbpbindir . "/" . $outputusbfile);
				
	foreach my $key (sort { lc($a) cmp lc($b) } keys %$config) {
		$usb_list.= "<option value=" . $key . ">" . $config->{$key}->{name}, $key . "</option>\n";
    }
	$template->param("USB_LIST", $usb_list);
	
	# detect Soundcards
	system($lbpbindir . '/service.sh sc_show');
	my $filename = '/tmp/soundcards2.txt';
	open my $in, $filename;
	my $sc_list;
	while (my $line = <$in>) {
            $sc_list.= $line.'<br>';
        }
    $template->param("SC_LIST", $sc_list);
	close($in);
	
	# check/get filesize of determined soundcards in order to fadeIn/fadeOut
	my $filesize = -s $devicefile;
	$template->param("MYFILE", $filesize);
		
	LOGDEB "Printing template";
	printtemplate();
	
	#Test Print to UI
	#my $content =  "Miniserver Nr. 1 heißt: $MiniServer und hat den Port: $MSWebPort User ist: $MSUser und PW: $MSPass.";
	#my $template_title = 'Testing';
	#LoxBerry::Web::lbheader($template_title);
	#print "Size: $filesize\n";
	#LoxBerry::Web::lbfooter();
	#exit;
}

#####################################################
# Save-Sub
#####################################################

sub save 
{
	LOGTITLE "Save parameters";
	
	# Check, if filename for the successtemplate is readable
	stat($lbptemplatedir . "/" . $successtemplatefilename);
	if ( !-r _ )
	{
		$error_message = $SL{'ERRORS.ERR_SUCCESS_TEMPLATE_NOT_READABLE'};
		LOGCRIT "The ".$successtemplatefilename." file could not be loaded. Abort plugin loading";
		LOGERR $error_message;
		&error;
	}
	LOGDEB "Filename for the successtemplate is ok, preparing template";
	my $successtemplate = 	HTML::Template->new(
							filename => $lbptemplatedir . "/" . $successtemplatefilename,
							global_vars => 1,
							loop_context_vars => 1,
							die_on_bad_params=> 0,
							associate => $cgi,
							%htmltemplate_options,
							debug => 1,
							);
	my %SUC = LoxBerry::System::readlanguage($successtemplate, $languagefile);

	LOGDEB "Filling config with parameters";

	# Write configuration file(s)
	$pcfg->param("TTS.t2s_engine", "$R::t2s_engine");
	$pcfg->param("TTS.messageLang", "$R::t2slang");
	$pcfg->param("TTS.API-key", "$R::apikey");
	$pcfg->param("TTS.secret-key", "$R::seckey");
	$pcfg->param("TTS.voice", "$R::voice");
	$pcfg->param("TTS.regionms", $azureregion);
	$pcfg->param("MP3.file_gong", "$R::file_gong");
	$pcfg->param("MP3.MP3store", "$R::mp3store");
	$pcfg->param("MP3.cachesize", "$R::cachesize");
	$pcfg->param("LOCATION.town", "$R::town");
	$pcfg->param("LOCATION.region", "$R::region");
	$pcfg->param("LOCATION.googlekey", "$R::googlekey");
	$pcfg->param("LOCATION.googletown", "$R::googletown");
	$pcfg->param("LOCATION.googlestreet", "$R::googlestreet");
	$pcfg->param("VARIOUS.CALDavMuell", "$R::wastecal");
	$pcfg->param("VARIOUS.CALDav2", "$R::cal");
	#$pcfg->param("SYSTEM.LOGLEVEL", "$R::LOGLEVEL");
	$pcfg->param("SYSTEM.path", "$R::STORAGEPATH");
	$pcfg->param("SYSTEM.mp3path", "$R::STORAGEPATH/$mp3folder");
	$pcfg->param("SYSTEM.ttspath", "$R::STORAGEPATH/$ttsfolder");
	#$pcfg->param("SYSTEM.interfacepath", "$R::STORAGEPATH/$interfacefolder");
	$pcfg->param("SYSTEM.httpinterface", "http://$lbhostname/plugins/$lbpplugindir/interfacedownload");
	$pcfg->param("SYSTEM.cifsinterface", "//$lbhostname/plugindata/$lbpplugindir/interfacedownload");
	$pcfg->param("SYSTEM.card", "$R::out_list");
	$pcfg->param("SYSTEM.usbcard", "$R::usb_list");
	$pcfg->param("SYSTEM.usbdevice", "$R::usbdeviceno");
	$pcfg->param("SYSTEM.usbcardno", "$R::usbcardno");
	$pcfg->param("TTS.volume", "$R::volume");
	
	LOGINF "Writing configuration file";
	
	$pcfg->save() or &error;

	LOGOK "All settings has been saved successful";

	# If storage folders do not exist, copy default mp3 files
	my $copy = 0;
	if (!-e "$R::STORAGEPATH/$mp3folder") {
		$copy = 1;
	}

	LOGINF "Creating folders and symlinks";
	system ("mkdir -p $R::STORAGEPATH/$mp3folder");
	system ("mkdir -p $R::STORAGEPATH/$ttsfolder");
	#system ("mkdir -p $R::STORAGEPATH/$interfacefolder");
	system ("rm $lbpdatadir/interfacedownload");
	system ("rm $lbphtmldir/interfacedownload");
	system ("ln -s $R::STORAGEPATH/$ttsfolder $lbpdatadir/interfacedownload");
	system ("ln -s $R::STORAGEPATH/$ttsfolder $lbphtmldir/interfacedownload");
	LOGOK "All folders and symlinks created successfully.";

	if ($copy) {
		LOGINF "Copy existing mp3 files from $lbpdatadir/$mp3folder to $R::STORAGEPATH/$mp3folder";
		system ("cp -r $lbpdatadir/$mp3folder/* $R::STORAGEPATH/$mp3folder");
	}

	$lblang = lblanguage();
	$template_title = "$SL{'BASIS.MAIN_TITLE'}: v$sversion";
	LoxBerry::Web::lbheader($template_title, $helplink, $helptemplatefilename);
	$successtemplate->param('SAVE_ALL_OK'		, $SUC{'SAVE.SAVE_ALL_OK'});
	$successtemplate->param('SAVE_MESSAGE'		, $SUC{'SAVE.SAVE_MESSAGE'});
	$successtemplate->param('SAVE_BUTTON_OK' 	, $SUC{'SAVE.SAVE_BUTTON_OK'});
	$successtemplate->param('SAVE_NEXTURL'		, $ENV{REQUEST_URI});
	LOGDEB "Printing success template";
	print $successtemplate->output();
	LoxBerry::Web::lbfooter();
	exit;
	
	# Test Print to UI
	#my $content =  "http://$MSUser:$MSPass\@$MiniServer:$MSWebPort/dev/sps/io/fetch_sonos/Ein";
	#my $template_title = '';
	#LoxBerry::Web::lbheader($template_title);
	#print $content;
	#LoxBerry::Web::lbfooter();
	#exit;
		
}


#####################################################
# Error-Sub
#####################################################

sub error 
{
	LOGTITLE "Show error form";
		
	# Check, if filename for the errortemplate is readable
	stat($lbptemplatedir . "/" . $errortemplatefilename);
	if ( !-r _ )
	{
		$error_message = $no_error_template_message;
		LoxBerry::Web::lbheader($template_title, $helplink, $helptemplatefilename);
		print $error_message;
		LOGCRIT $error_message;
		LoxBerry::Web::lbfooter();
		LOGERR "Leave Plugin due to an critical error";
		exit;
	}

	# Filename for the errortemplate is ok, preparing template";
	my $errortemplate = HTML::Template->new(
						filename => $lbptemplatedir . "/" . $errortemplatefilename,
						global_vars => 1,
						loop_context_vars => 1,
						die_on_bad_params=> 0,
						associate => $cgi,
						%htmltemplate_options,
						# debug => 1,
						);
	my %ERR = LoxBerry::System::readlanguage($errortemplate, $languagefile);

	#**************************************************************************
	
	$template_title = $SL{'ERRORS.MY_NAME'} . ": v$sversion - " . $SL{'ERRORS.ERR_TITLE'};
	LoxBerry::Web::lbheader($template_title, $helplink, $helptemplatefilename);
	$errortemplate->param('ERR_MESSAGE'		, $error_message);
	$errortemplate->param('ERR_TITLE'		, $SL{'ERRORS.ERR_TITLE'});
	$errortemplate->param('ERR_BUTTON_BACK' , $SL{'ERRORS.ERR_BUTTON_BACK'});
	$errortemplate->param('ERR_NEXTURL'	, $ENV{REQUEST_URI});
	print $errortemplate->output();
	LoxBerry::Web::lbfooter();
	exit;
}


##########################################################################
# Init Template
##########################################################################
sub inittemplate
{
	# Check, if filename for the maintemplate is readable, if not raise an error
	stat($lbptemplatedir . "/" . $maintemplatefilename);
	if ( !-r _ )
	{
		$error_message = "Error: Main template not readable";
		LOGCRIT "The ".$maintemplatefilename." file could not be loaded. Abort plugin loading";
		LOGCRIT $error_message;
		&error;
	}

	$template =  HTML::Template->new(
				filename => $lbptemplatedir . "/" . $maintemplatefilename,
				global_vars => 1,
				loop_context_vars => 1,
				die_on_bad_params=> 0,
				associate => $pcfg,
				%htmltemplate_options,
				debug => 1
				);
	%SL = LoxBerry::System::readlanguage($template, $languagefile);			

}

##########################################################################
# Print Template
##########################################################################
sub printtemplate
{
	# Print Template
	$template_title = "$SL{'BASIS.MAIN_TITLE'}: v$sversion";
	LoxBerry::Web::head();
	LoxBerry::Web::pagestart($template_title, $helplink, $helptemplate);
	print LoxBerry::Log::get_notifications_html($lbpplugindir);
	print $template->output();
	LoxBerry::Web::lbfooter();
	LOGOK "Website printed";
	exit;
}	

##########################################################################
# END routine - is called on every exit (also on exceptions)
##########################################################################
sub END 
{	
	our @reason;
	
	if ($log) {
		if (@reason) {
			LOGCRIT "Unhandled exception catched:";
			LOGERR @reason;
			LOGEND "Finished with an exception";
		} elsif ($error_message) {
			LOGEND "Finished with handled error";
		} else {
			LOGEND "Finished successful";
		}
	}
}



