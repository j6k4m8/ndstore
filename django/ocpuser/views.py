# Copyright 2014 Open Connectome Project (http://openconnecto.me)
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


import django.http
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.template import Context
from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User
from django.conf import settings
from django.forms.models import inlineformset_factory
import django.forms
from datetime import datetime
from contextlib import closing
import string
import random
import MySQLdb
import json
import re

import ocpcarest
import ocpcaproj
import jsonprojinfo
from ocptype import IMAGE, ANNOTATION, TIMESERIES, UINT8, UINT16, UINT32, UINT64, FLOAT32, OCP_VERSION, SCHEMA_VERSION 

from models import Project
from models import Dataset
from models import Token
from models import Channel
from models import Backup

from forms import ProjectForm
from forms import DatasetForm
from forms import TokenForm
from forms import ChannelForm
from forms import BackupForm
from forms import dataUserForm

from django.core.urlresolvers import get_script_prefix
import os
import subprocess
from ocpcaerror import OCPCAError

import logging
logger=logging.getLogger("ocp")

# Helpers

''' Base url redirects to projects page'''
def default(request):
  return redirect(get_script_prefix()+'ocpuser/projects', {"user":request.user})

''' Little welcome message'''
@login_required(login_url='/ocp/accounts/login/')
def getProjects(request):

  try:
    if request.method == 'POST':
      if 'filter' in request.POST:
        #FILTER PROJECTS BASED ON INPUT VALUE
        userid = request.user.id
        filteroption = request.POST.get('filteroption')
        filtervalue = (request.POST.get('filtervalue')).strip()
        
        pd = ocpcaproj.OCPCAProjectsDB()

        # get the visible data sets
        if request.user.is_superuser:
          visible_datasets=Dataset.objects.all()
        else:
          visible_datasets=Dataset.objects.filter(user_id=userid) | Dataset.objects.filter(public=1)

        visible_datasets.sort()

        projs = defaultdict(list)

        dbs = defaultdict(list)

        for db in visible_datasets:
          proj = Project.objects.filter(dataset_id=db.dataset_name, user_id=userid) | Project.objects.filter(dataset_id=db.dataset_name, public=1)
          if proj:
            dbs[db.dataset_name].append(proj)
          else:
            dbs[db.dataset_name].append(None)

        if request.user.is_superuser:
          visible_projects = Project.objects.all()
        else:
          visible_projects = Project.objects.filter(user_id=userid) | Project.objects.filter(public=1) 

        return render_to_response('projects.html', { 'databases': dbs.iteritems() ,'projects': visible_projects.values_list(flat=True) },context_instance=RequestContext(request))

      elif 'delete_data' in request.POST:

        pd = ocpcaproj.OCPCAProjectsDB()
        username = request.user.username
        project_to_delete = (request.POST.get('project_name')).strip()
                
        reftokens = Token.objects.filter(project_id=project_to_delete)
        if reftokens:
          messages.error(request, 'Project cannot be deleted. Please delete all tokens for this project first.')
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')
        else:
          proj = Project.objects.get(project_name=project_to_delete)
          if proj:
            if proj.user_id == request.user.id or request.user.is_superuser:
              #Delete project from the table followed  by the database.
              # deleting a project is super dangerous b/c you may delete it out from other tokens.
              #  on other servers.  So, only delete when it's on the same server for now
              pd.deleteOCPCADB(project_to_delete)
              proj.delete()          
              messages.success(request,"Project deleted")
            else:
              messages.error(request,"Cannot delete.  You are not owner of this project or not superuser.")
          else:
            messages.error( request,"Project not found.")
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')

      elif 'delete' in request.POST:
        pd = ocpcaproj.OCPCAProjectsDB()
        username = request.user.username
        project_to_delete = (request.POST.get('project_name')).strip()
                
        reftokens = Token.objects.filter(project_id=project_to_delete)
        if reftokens:
          messages.error(request, 'Project cannot be deleted. Please delete all tokens for this project first.')
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')
        else:
          proj = Project.objects.get(project_name=project_to_delete)
          if proj:
            if proj.user_id == request.user.id or request.user.is_superuser:
              proj.delete()          
              messages.success(request,"Project deleted")
            else:
              messages.error(request,"Cannot delete.  You are not owner of this project or not superuser.")
          else:
            messages.error( request,"Project not found.")
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')
      
      elif 'info' in request.POST:
      #GET PROJECT INFO -----------
        token = (request.POST.get('roptions')).strip()
        return HttpResponse(ocpcarest.projInfo(token), content_type="product/hdf5" )
      
      elif 'update' in request.POST:
        project_to_update =(request.POST.get('project_name')).strip() 
        request.session["project_name"] = project_to_update
        return redirect(updateProject)
      
      elif 'tokens' in request.POST:
        projname=(request.POST.get('project_name')).strip()
        request.session["project"] = projname
        return redirect(getTokens)

      elif 'channels' in request.POST:
        projname=(request.POST.get('project_name')).strip()
        request.session["project"] = projname
        return redirect(getChannels)

      elif 'backup' in request.POST:
        projname=(request.POST.get('project_name')).strip()
        request.session["project"] = projname
        return redirect(backupProject)
 
      else:
        # Invalid POST
        messages.error(request,"Unrecognized POST")
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')

    else:
    # GET Projects
      userid = request.user.id

      # get the visible data sets
      if request.user.is_superuser:
        visible_datasets=Dataset.objects.all()
      else:
        visible_datasets=Dataset.objects.filter(user_id=userid) | Dataset.objects.filter(public=1)

      dbs = defaultdict(list)
    
      for db in visible_datasets:
        proj = Project.objects.filter(dataset_id=db.dataset_name, user_id=userid) | Project.objects.filter(dataset_id=db.dataset_name, public=1)
        if proj:
          dbs[db.dataset_name].append(proj)
        else:
          dbs[db.dataset_name].append(None)
      
      if request.user.is_superuser:
        visible_projects = Project.objects.all()
      else:
        visible_projects = Project.objects.filter(user_id=userid) | Project.objects.filter(public=1) 

      return render_to_response('projects.html', { 'databases': sorted(dbs.iteritems()) ,'projects':visible_projects },context_instance=RequestContext(request))
    
  except OCPCAError, e:

    messages.error(request,"Exception in administrative interface = {}".format(e)) 

    # GET Projects
    username = request.user.username
    all_datasets= Dataset.objects.all()
    dbs = defaultdict(list)
    for db in all_datasets:
      proj = Project.objects.filter(dataset_id=db.dataset_name, user_id = request.user)
      if proj:
        dbs[db.dataset_name].append(proj)
      else:
        dbs[db.dataset_name].append(None)
    
    all_projects = Project.objects.values_list('project_name',flat= True)
    return render_to_response('projects.html', { 'databases': dbs.iteritems() ,'projects':all_projects },context_instance=RequestContext(request))
    

@login_required(login_url='/ocp/accounts/login/')
def getDatasets(request):

  try:

    pd = ocpcaproj.OCPCAProjectsDB()

    userid = request.user.id
    if request.user.is_superuser:
      visible_datasets=Dataset.objects.all()
    else:
      visible_datasets= Dataset.objects.filter(user_id=userid) | Dataset.objects.filter(public=1)

    if request.method == 'POST':

      if 'filter' in request.POST:
        filtervalue = (request.POST.get('filtervalue')).strip()
        visible_datasets = visible_datasets.filter(dataset_name=filtervalue)
        return render_to_response('datasets.html', { 'dts': visible_datasets },context_instance=RequestContext(request))

      elif 'delete' in request.POST:

        #delete specified dataset
        ds = (request.POST.get('dataset_name')).strip()
        ds_to_delete = Dataset.objects.get(dataset_name=ds)
        
        # Check for projects with that dataset
        proj = Project.objects.filter(dataset_id=ds_to_delete.dataset_name)
        if proj:
          messages.error(request, 'Dataset cannot be deleted. Please delete all projects for this dataset first.')
        else:
          if ds_to_delete.user_id == request.user.id or request.user.is_superuser:
            ds_to_delete.delete()
            messages.success(request, 'Deleted Dataset ' + ds)
          else:
            messages.error(request,"Cannot delete.  You are not owner of this dataset or not superuser.")

          # refresh to remove deleted
          if request.user.is_superuser:
            visible_datasets=Dataset.objects.all()
          else:
            visible_datasets=Dataset.objects.filter(user=request.user.id) | Dataset.objects.filter(public=1)

        return render_to_response('datasets.html', { 'dts': visible_datasets },context_instance=RequestContext(request))
      elif 'update' in request.POST:
        ds = (request.POST.get('dataset_name')).strip()
        request.session["dataset_name"] = ds
        return redirect(updateDataset)

      else:
        #Load datasets
        return render_to_response('datasets.html', { 'dts': visible_datasets },context_instance=RequestContext(request))

    else:
      # GET datasets
      return render_to_response('datasets.html', { 'dts': visible_datasets },context_instance=RequestContext(request))

  except OCPCAError, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return render_to_response('datasets.html', { 'dts': visible_datasets },context_instance=RequestContext(request))    

@login_required(login_url='/ocp/accounts/login/')
def getAllTokens(request):

  if 'filter' in request.POST:
    del request.session['filter']
  if 'project' in request.session:
    del request.session['project']

  return getTokens(request)


@login_required(login_url='/ocp/accounts/login/')
def getChannels(request):

  username = request.user.username
  pd = ocpcaproj.OCPCAProjectsDB()  

  try:
    if request.method == 'POST':

      if 'delete' in request.POST:
        # Delete the channel from the project
        channel_to_delete = (request.POST.get('channel')).strip()
        prname = request.session["project"]
        pr = Project.objects.get(project_name=prname)
        ch = Channel.objects.get(channel_name=channel_to_delete, project_id=pr )
        if ch:
          if pr.user_id == request.user.id or request.user.is_superuser:
            pd.deleteOCPCAChannel(pr, ch.channel_name)
            ch.delete()
            messages.success(request,"Channel deleted " + channel_to_delete)
          else:
            messages.error(request,"Cannot delete.  You are not owner of this token or not superuser.")
        else:
          messages.error(request,"Unable to delete " + channel_to_delete)
        return redirect(getChannels)

      # update form populated with channel fields
      elif 'update' in request.POST:
        channel = (request.POST.get('channel')).strip()
        request.session["channel_name"] = channel
        return redirect(updateChannel)

      # add using the update channel form with no initial data
      elif 'add' in request.POST:
        # must remove channel_name context to add a new one.  otherwise, it's an update
        if "channel_name" in request.session:
          del ( request.session["channel_name"] )
        return redirect(updateChannel)

      elif 'backtochannels' in request.POST:
        return redirect(getChannels)

      elif 'backtoprojects' in request.POST:
        return redirect(getProjects)


      else:
        # Unrecognized Option
        messages.error(request,"Invalid request")
        return redirect(getChannels)

    else:
      # GET tokens for the specified project
      username = request.user.username
      if "project" in request.session:
        proj = request.session["project"]
        all_channels = Channel.objects.filter(project_id=proj)
      else:
        # Unrecognized Option
        messages.error(request, "Must have a project context to look at channels.")
        return redirect(getChannels)
      print all_channels
      return render_to_response('channels.html', { 'channels': all_channels, 'project': proj },context_instance=RequestContext(request))
    
  except OCPCAError, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    datasets = pd.getDatasets()
    return render_to_response('projects.html',context,context_instance=RequestContext(request))
 

@login_required(login_url='/ocp/accounts/login/')
def getTokens(request):

  username = request.user.username
  pd = ocpcaproj.OCPCAProjectsDB()  

  try:
    if request.method == 'POST':
      if 'filter' in request.POST:
        # Filter tokens based on an input value
        filteroption = request.POST.get('filteroption')
        filtervalue = (request.POST.get('filtervalue')).strip()
        all_tokens = Token.objects.filter(token_name=filtervalue)
        proj=""
        return render_to_response('tokens.html', { 'tokens': all_tokens, 'project': proj },context_instance=RequestContext(request))

      elif 'delete' in request.POST:
        # Delete the token from the token table
        token_to_delete = (request.POST.get('token')).strip()
        token = Token.objects.get(token_name=token_to_delete)
        if token:
          if token.user_id == request.user.id or request.user.is_superuser:
            token.delete()          
            messages.success(request,"Token deleted " + token_to_delete)
          else:
            messages.error(request,"Cannot delete.  You are not owner of this token or not superuser.")
        else:
          messages.error(request,"Unable to delete " + token_to_delete)
        return redirect(getTokens)

      elif 'downloadtoken' in request.POST:
        # Download the token in a test file
        token = (request.POST.get('token')).strip()
        response = HttpResponse(token,content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="ocpca.token"'
        return response

      elif 'update' in request.POST:
        # update project token
        token = (request.POST.get('token')).strip()
        request.session["token_name"] = token
        return redirect(updateToken)

      # redirect to add a token
      elif 'add' in request.POST:
        return redirect(createToken)

      elif 'backtoprojects' in request.POST:
         return redirect(getProjects) 

      else:
        # Unrecognized Option
        messages.error(request,"Invalid request")
        return redirect(getTokens)

    else:
      # GET tokens for the specified project
      username = request.user.username
      if "project" in request.session:
        proj = request.session["project"]
        all_tokens = Token.objects.filter(project_id=proj)
      else:
        proj=""
        all_tokens = Token.objects.all()
      return render_to_response('tokens.html', { 'tokens': all_tokens, 'project': proj },context_instance=RequestContext(request))
    
  except OCPCAError, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    datasets = pd.getDatasets()
    return render_to_response('datasets.html', { 'dts': datasets },context_instance=RequestContext(request))


@login_required(login_url='/ocp/accounts/login/')
def createProject(request):

  try:
    pd = ocpcaproj.OCPCAProjectsDB()  

    if request.method == 'POST':
      if 'createproject' in request.POST:

        form = ProjectForm(request.POST)
        
        if form.is_valid():
          new_project=form.save(commit=False)
          new_project.user_id=request.user.id
          if request.POST.get('legacy') == 'yes':
            new_project.ocp_version='0.0'
          else:
            new_project.ocp_version=OCP_VERSION
          new_project.schema_version=SCHEMA_VERSION
          new_project.save()
          try:
            # create a database when not linking to an existing databases
            if not request.POST.get('nocreate') == 'on':
              pd.newOCPCAProject( new_project.project_name )
            if 'token' in request.POST:
              tk = Token ( token_name = new_project.project_name, token_description = 'Default token for public project', project_id=new_project, user_id=request.user.id, public=new_project.public ) 
              tk.save()

          except Exception, e:
            logger.error("Failed to create project.  Error {}".format(e))
            messages.error(request,"Failed to create project Error {}".format(e))

          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects/')
        else:
          context = {'form': form}
          return render_to_response('createproject.html',context,context_instance=RequestContext(request))

      else:
        #default
        return redirect(getProjects)

    else:
      '''Show the Create Project form'''

      form = ProjectForm()

      # restrict datasets to user visible fields
      form.fields['dataset'].queryset = Dataset.objects.filter(user_id=request.user.id) | Dataset.objects.filter(public=1)

      context = {'form': form}
      return render_to_response('createproject.html',context,context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects/')

      
@login_required(login_url='/ocp/accounts/login/')
def createDataset(request):
 
  try:
    if request.method == 'POST':
      if 'createdataset' in request.POST:
        form = DatasetForm(request.POST)
        if form.is_valid():
          new_dataset=form.save(commit=False)
          new_dataset.user_id=request.user.id
          new_dataset.save()
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/datasets')
        else:
          context = {'form': form}
          return render_to_response('createdataset.html',context,context_instance=RequestContext(request))
      elif 'backtodatasets' in request.POST:
        return redirect(getDatasets)
      else:
        #default
        messages.error(request,"Unkown POST request.")
        return redirect(getDatasets)
    else:
      '''Show the Create datasets form'''
      form = DatasetForm()
      context = {'form': form}
      return render_to_response('createdataset.html',context,context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    datasets = pd.getDatasets()
    return render_to_response('datasets.html', { 'dts': datasets },context_instance=RequestContext(request))


@login_required(login_url='/ocp/accounts/login/')
def updateDataset(request):

  try:
    # Get the dataset to update
    ds = request.session["dataset_name"]
    if request.method == 'POST':
      if 'updatedataset' in request.POST:
        ds_update = get_object_or_404(Dataset,dataset_name=ds)

        if ds_update.user_id == request.user.id or request.user.is_superuser:

          form = DatasetForm(data=request.POST or None,instance=ds_update)
          if form.is_valid():
            form.save()
            messages.success(request, 'Sucessfully updated dataset')
            del request.session["dataset_name"]
            return HttpResponseRedirect(get_script_prefix()+'ocpuser/datasets')
          else:
            #Invalid form
            context = {'form': form}
            return render_to_response('updatedataset.html',context,context_instance=RequestContext(request))

        else:
          messages.error(request,"Cannot update.  You are not owner of this dataset or not superuser.")
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/datasets')

      elif 'backtodatasets' in request.POST:
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/datasets')
      else:
        #unrecognized option
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/datasets')
    else:
      print "Getting the update form"
      if "dataset_name" in request.session:
        ds = request.session["dataset_name"]
      else:
        ds = ""
      ds_to_update = Dataset.objects.filter(dataset_name=ds)
      data = {
        'dataset_name': ds_to_update[0].dataset_name,
        'ximagesize':ds_to_update[0].ximagesize,
        'yimagesize':ds_to_update[0].yimagesize,
        'zimagesize':ds_to_update[0].zimagesize,
        'xoffset':ds_to_update[0].xoffset,
        'yoffset':ds_to_update[0].yoffset,
        'zoffset':ds_to_update[0].zoffset,
        'public':ds_to_update[0].public,
        'xvoxelres':ds_to_update[0].xvoxelres,
        'yvoxelres':ds_to_update[0].yvoxelres,
        'zvoxelres':ds_to_update[0].zvoxelres,
        'scalinglevels':ds_to_update[0].scalinglevels,
        'scalingoption':ds_to_update[0].scalingoption,
        'starttime':ds_to_update[0].starttime,
        'endtime':ds_to_update[0].endtime,
        'dataset_description':ds_to_update[0].dataset_description,
              }
      form = DatasetForm(initial=data)
      context = {'form': form}
      return render_to_response('updatedataset.html',context,context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    datasets = pd.getDatasets()
    return render_to_response('datasets.html', { 'dts': datasets },context_instance=RequestContext(request))


@login_required(login_url='/ocp/accounts/login/')
def updateChannel(request):

  try:
    prname = request.session['project']
    pr = Project.objects.get ( project_name = prname )
    pd = ocpcaproj.OCPCAProjectsDB()

    if request.method == 'POST':

      if 'updatechannel' in request.POST: 

        chname = request.session["channel_name"]
        channel_to_update = get_object_or_404(Channel,channel_name=chname,project_id=pr)
        form = ChannelForm(data=request.POST or None, instance=channel_to_update)

        if form.is_valid():
          newchannel = form.save(commit=False)

        else:
          # Invalid form
          context = {'form': form, 'project': prname}
          return render_to_response('updatechannel.html', context, context_instance=RequestContext(request))

      elif 'propagatechannel' in request.POST:

        chname = request.session["channel_name"]
        channel_to_update = get_object_or_404(Channel,channel_name=chname,project_id=pr)
        form = ChannelForm(data=request.POST or None, instance=channel_to_update)

        # KLTODO/RBTODO add propagate to the UI
  #      messages.error(request,"Propagate not yet implemented in self-admin UI.")
  #      return HttpResponseRedirect(get_script_prefix()+'ocpuser/channels')

        context = {'form': form, 'project': prname}
        form.add_error(None,[u"Propagate not yet implemented in self-admin UI."])
        return render_to_response('updatechannel.html', context, context_instance=RequestContext(request))

      elif 'createchannel' in request.POST:

        form = ChannelForm(data=request.POST or None)

        if form.is_valid():

          new_channel = form.save( commit=False )

          # populate the channel type and data type from choices
          combo = request.POST.get('channelcombo')
          if combo=='i:8':
            new_channel.channel_type = IMAGE
            new_channel.channel_datatype = UINT8
          elif combo=='i:16':
            new_channel.channel_type = IMAGE
            new_channel.channel_datatype = UINT16
          elif combo=='i:32':
            new_channel.channel_type = IMAGE
            new_channel.channel_datatype = UINT32
          elif combo=='a:32':
            new_channel.channel_type = ANNOTATION
            new_channel.channel_datatype = UINT32
          elif combo=='f:32':
            new_channel.channel_type = IMAGE
            new_channel.channel_datatype = FLOAT32
          elif combo=='t:8':
            new_channel.channel_type = TIMESERIES
            new_channel.channel_datatype = UINT8
          elif combo=='t:16':
            new_channel.channel_type = TIMESERIES
            new_channel.channel_datatype = UINT16
          elif combo=='t:32':
            new_channel.channel_type = TIMESERIES
            new_channel.channel_datatype = FLOAT32
          else:
            logger.error("Illegal channel combination requested: {}.".format(combo))
            messages.error(request,"Illegal channel combination requested or none selected.")
            return HttpResponseRedirect(get_script_prefix()+'ocpuser/channels')

          if pr.user_id == request.user.id or request.user.is_superuser:

            # if there is no default channel, make this default
            if not Channel.objects.filter(project_id=pr, default=True):
              new_channel.default = True

            new_channel.save()

            if not request.POST.get('nocreate') == 'on':

              try:
                # create the tables for the channel
                pd.newOCPCAChannel( pr.project_name, new_channel.channel_name)
              except Exception, e:
                logger.error("Failed to create channel. Error {}".format(e))
                messages.error(request,"Failed to create channel. {}".format(e))
                new_channel.delete()

            return HttpResponseRedirect(get_script_prefix()+'ocpuser/channels')

          else:
            messages.error(request,"Cannot update.  You are not owner of this token or not superuser.")
            return HttpResponseRedirect(get_script_prefix()+'ocpuser/channels')

        else:
          #Invalid form
          context = {'form': form, 'project': prname}
          return render_to_response('createchannel.html', context, context_instance=RequestContext(request))

      else:
        #unrecognized option
        return redirect(getChannels)

      if pr.user_id == request.user.id or request.user.is_superuser:
   
        # if setting the default channel, remove previous default
        if newchannel.default == True:
          olddefault = Channel.objects.filter(default=True, project_id=pr)    
          for od in olddefault:
            od.default = False
            od.save()

        # if there is no default channel, make this default
        if not Channel.objects.filter(project_id=pr):
          newchannel.default = True

        newchannel.save()
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/channels')

      else:
        messages.error(request,"Cannot update.  You are not owner of this token or not superuser.")
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/channels')

    else:
      if "channel_name" in request.session:
        chname = request.session["channel_name"]
        channel_to_update = Channel.objects.filter(project_id=pr).filter(channel_name=chname)
        data = {
          'channel_name': channel_to_update[0].channel_name,
          'channel_type':channel_to_update[0].channel_type,
          'channel_datatype': channel_to_update[0].channel_datatype,
          'channel_description':channel_to_update[0].channel_description,
          'readonly':channel_to_update[0].readonly,
          'resolution':channel_to_update[0].resolution,
          'default':channel_to_update[0].default,
          'exceptions':channel_to_update[0].exceptions,
          'propagate':channel_to_update[0].propagate,
          'startwindow':channel_to_update[0].startwindow,
          'endwindow':channel_to_update[0].endwindow,
          'project': pr
        }
        form = ChannelForm(initial=data)
        context = {'form': form, 'project': prname }
        return render_to_response('updatechannel.html', context, context_instance=RequestContext(request))
      else:
        data = {
          'project': pr
        }
        form = ChannelForm(initial=data)
        context = {'form': form, 'project': prname }
        return render_to_response('createchannel.html', context, context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return redirect(get_script_prefix()+'projects', {"user":request.user})


@login_required(login_url='/ocp/accounts/login/')
def updateToken(request):

  try:
    # Get the dataset to update
    token = request.session["token_name"]
    if request.method == 'POST':
      if 'updatetoken' in request.POST:
        token_update = get_object_or_404(Token,token_name=token)
        form = TokenForm(data=request.POST or None, instance=token_update)
        if form.is_valid():
          newtoken = form.save( commit=False )
          if newtoken.user_id == request.user.id or request.user.is_superuser:
            # if you changed the token name, delete old token
            newtoken.save()
            if newtoken.token_name != token:
              deltoken = Token.objects.filter(token_name=token)
              deltoken.delete()
            messages.success(request, 'Sucessfully updated Token')
            del request.session["token_name"]
          else:
            messages.error(request,"Cannot update.  You are not owner of this token or not superuser.")
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/token')
        else:
          #Invalid form
          context = {'form': form}
          return render_to_response('updatetoken.html',context,context_instance=RequestContext(request))
      elif 'backtotokens' in request.POST:
        #unrecognized option
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/token')
      else:
        #unrecognized option
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/token')
    else:
      print "Getting the update form"
      if "token_name" in request.session:
        token = request.session["token_name"]
      else:
        token = ""
      token_to_update = Token.objects.filter(token_name=token)
      data = {
        'token_name': token_to_update[0].token_name,
        'token_description':token_to_update[0].token_description,
        'project':token_to_update[0].project_id,
        'public':token_to_update[0].public,
      }
      form = TokenForm(initial=data)
      context = {'form': form}
      return render_to_response('updatetoken.html',context,context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return redirect(get_script_prefix()+'projects', {"user":request.user})


@login_required(login_url='/ocp/accounts/login/')
def updateProject(request):

  try:
    proj_name = request.session["project_name"]
    if request.method == 'POST':
      
      if 'UpdateProject' in request.POST:
        proj_update = get_object_or_404(Project,project_name=proj_name)
        form = ProjectForm(data= request.POST or None,instance=proj_update)
        if form.is_valid():
          newproj = form.save(commit=False)
          if newproj.user_id == request.user.id or request.user.is_superuser:
            if newproj.project_name != proj_name:
              messages.error ("Cannot change the project name.  MySQL cannot rename databases.")
            else:
              newproj.save()
              messages.success(request, 'Sucessfully updated project ' + proj_name)
          else:
            messages.error(request,"Cannot update.  You are not owner of this project or not superuser.")
          del request.session["project_name"]
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')
        else:
          #Invalid form
          context = {'form': form}
          return render_to_response('updateproject.html',context,context_instance=RequestContext(request))
      elif 'backtoprojects' in request.POST:
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')
      else:
        #unrecognized option
        messages.error(request,"Unrecognized Post")
        return HttpResponseRedirect(get_script_prefix()+'ocpuser/pojects')
        
    else:
      #Get: Retrieve project and display update project form.
      if "project_name" in request.session:
        proj = request.session["project_name"]
      else:
        proj = ""
      project_to_update = Project.objects.filter(project_name=proj)
      data = {
        'project_name': project_to_update[0].project_name,
        'project_description':project_to_update[0].project_description,
        'dataset':project_to_update[0].dataset_id,
        'public':project_to_update[0].public,
        'host':project_to_update[0].host,
        'kvengine':project_to_update[0].kvengine,
        'kvserver':project_to_update[0].kvserver,
      }
      form = ProjectForm(initial=data)
      context = {'form': form}
      return render_to_response('updateproject.html',context,context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return redirect(get_script_prefix()+'projects', {"user":request.user})

@login_required(login_url='/ocp/accounts/login/')
def createToken(request):

  try:
    prname = request.session['project']
    pr = Project.objects.get ( project_name = prname )

    if request.method == 'POST':
      if 'createtoken' in request.POST:

        form = TokenForm(request.POST)

        # restrict projects to user visible fields
        form.fields['project'].queryset = Project.objects.filter(user_id=request.user.id) | Project.objects.filter(public=1)

        if form.is_valid():
          new_token=form.save(commit=False)
          new_token.user_id=request.user.id
          new_token.save()
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')
        else:
          context = {'form': form}
          return render_to_response('createtoken.html',context,context_instance=RequestContext(request))
      elif 'backtotokens' in request.POST:
         return redirect(getTokens) 
      else:
        messages.error(request,"Unrecognized Post")
        redirect(getTokens)
    else:
      '''Show the Create datasets form'''

      data = {
        'project': pr
      }
      form = TokenForm( initial = data )
      context = {'form': form, 'project': prname }
      return render_to_response('createtoken.html',context,context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return redirect(get_script_prefix()+'ocpuser/projects', {"user":request.user})



@login_required(login_url='/ocp/accounts/login/')
def backupProject(request):
  """Backup some or all channels of a project"""

  try:
  
    # perform a backup
    if request.method == 'POST':
   
      if 'backup' in request.POST:

        form = BackupForm(request.POST)

        # bind the project
        prname = request.session["project"]

        if not form.is_valid():

          context = {'form': form, 'project': prname}
          return render_to_response('backup.html',context,context_instance=RequestContext(request))

        else:

          new_backup=form.save(commit=False)

          # backup to the local file system  -- only option for now
          # if new_backup.protocol == 'local':
          if True:

            # Get the database information
            dbname = (request.POST.get('project')).strip()
            pr = Project.objects.get(project_name=prname)

            if request.POST.get('allchans') == 'on':
              channel ='all'
            elif new_backup.channel != None:
              channel = new_backup.channel.channel_name
            else:
              raise  OCPCAError ("Cannot backup specified channel {}".format(new_backup.channel))
              
            #RB restart here
            upath = '{}/{}'.format(settings.BACKUP_PATH,request.user.username)
            ppath = '{}/{}'.format(upath,dbname)
            fpath = '{}/{}'.format(ppath,channel)
            if not os.path.exists(upath):
              os.mkdir( upath, 0755 )
            if not os.path.exists(ppath):
              os.mkdir( ppath, 0755 )
            if not os.path.exists(fpath):
              os.mkdir( fpath, 0755 )

            # database output file
            ofile = '{}/{}.sql'.format(fpath,datetime.now().isoformat())
            dbuser = settings.DATABASES['default']['USER']
            passwd = settings.DATABASES['default']['PASSWORD']
            cmd = ['mysqldump', '-u'+ dbuser, '-p'+ passwd, '--single-transaction', '-h', pr.host, dbname]

            # json metadata file
            jfile = '{}/{}.json'.format(fpath,datetime.now().isoformat())

            # set the filenames
            new_backup.filename = ofile
            new_backup.jsonfile = jfile

            with closing ( open(jfile, 'w')) as jsonfp:
              with closing ( ocpcaproj.OCPCAProjectsDB() ) as projdb:
                proj = projdb.loadToken ( pr )
                jsonfp.write ( jsonprojinfo.jsonInfo(proj) )

            # if not all channels were requested
            if request.POST.get('allchans') == 'on':
              new_backup.channel = None
            else:
              # get list of tables
              with closing(MySQLdb.connect (host = pr.host, user = settings.DATABASES['default']['USER'], passwd = settings.DATABASES['default']['PASSWORD'], db = pr.project_name )) as newconn:
                with closing ( newconn.cursor() ) as newcursor:

                  # all channel tables have a common prefix with underscore
                  sql = "SHOW TABLES like \'{}_%\'".format(channel)
        
                  newcursor.execute(sql)
                  tables = newcursor.fetchall()
       
                for t in tables:
                  cmd.append(t[0]) 

            # backup now
            if request.POST.get('async'):

              outputfile = open(ofile, 'w') 
              p = subprocess.Popen(cmd, stdout=outputfile)

              new_backup.status = 1
              new_backup.protocol = 'MySQL'
              new_backup.save()

              messages.success(request, 'Initiated backup in background.  Project: {}'.format(dbname))

              # create a thread to monitor 
              import threading
              t = threading.Thread ( target=_monitorBackup, args=(p,new_backup,outputfile) )
              t.start()
              return HttpResponseRedirect(get_script_prefix()+'ocpuser/backupproject')

            else:

              with closing (open(ofile, 'w')) as outputfile:

                po = subprocess.Popen(cmd, stdout=outputfile)
                po.communicate(None)
                rc = po.returncode
                if rc<0:
                  raise OCPCAError("Backup process failed. Status = {}".format(rc))

              new_backup.status = 0
              new_backup.protocol = 'MySQL'
              new_backup.save()

              messages.success(request, 'Sucessfully backed up database '+ dbname)
              return HttpResponseRedirect(get_script_prefix()+'ocpuser/projects')

          elif new_backup.protocol == 's3':
            raise OCPCAError ("Unimplemented backup protocol: s3")
          else:
            raise OCPCAError ("Unkown protocol {}".format(new_backup.protocol))

      elif 'restore' in request.POST:
        request.session["backupid"] = (request.POST.get('backupid')).strip()
        return redirect(restoreProject)

      elif 'backtoprojects' in request.POST:
        return redirect(getProjects)


      elif 'delete' in request.POST:

        buid = (request.POST.get('backupid')).strip()

        try:
          bu_to_delete = Backup.objects.get ( backup_id=buid ) 
        except Backup.DoesNotExist:
          # no backup found
          raise

        #delete the files
        cmd = ['rm', bu_to_delete.filename ]
        po = subprocess.Popen(cmd)
        po.communicate(None)
        rc = po.returncode
        if rc<0:
          raise OCPCAError("Failed to delete backup file. Status = {}".format(rc))

        cmd = ['rm', bu_to_delete.jsonfile ]
        po = subprocess.Popen(cmd)
        po.communicate(None)
        rc = po.returncode
        if rc<0:
          raise OCPCAError("Failed to delete backup metadata file. Status = {}".format(rc))

        # remove the backup record
        bu_to_delete.delete()

        return HttpResponseRedirect(get_script_prefix()+'ocpuser/backupproject')

    # show the backup page
    else:
      """show the backup form"""

      # bind the project
      prname = request.session["project"]
      pr = Project.objects.get(project_name=prname)

      # get all channel choices
      channels = Channel.objects.filter(project_id=pr) 

      # list the backups
      backups = Backup.objects.filter(project_id=pr) 

      data = {
        'project': pr,
      }
      form = BackupForm(initial=data)

      # restrict datasets to user visible fields
      form.fields['channel'].queryset = channels

      context = {'form': form, 'project': prname, 'channels': channels, 'backups': backups }
      return render_to_response('backup.html', context, context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return redirect(get_script_prefix()+'ocpuser/projects', {"user":request.user})


@login_required(login_url='/ocp/accounts/login/')
def restoreProject ( request ):

  try:
    # perform a backup
    if request.method == 'POST':

      if 'createproject' in request.POST:
        """Create a new project from previous backup"""
      
        bu = Backup.objects.get ( backup_id=request.POST.get("buid") )
        pr = Project.objects.get ( project_name=bu.project_id )
        ds = Dataset.objects.get ( dataset_name=pr.dataset_id )

        jfp = open ( bu.jsonfile ) 
        projmd = json.load ( jfp )
       
        # setup the project
        newproj = Project()
        newproj.project_name = request.POST.get("project_name")
        newproj.project_description = request.POST.get("project_description")
        newproj.user_id = request.user.id
        newproj.public = request.POST.get("public")
        newproj.host = request.POST.get("host")
        newproj.kvengine = 'MySQL'
        newproj.kvserver = request.POST.get("host")
        newproj.dataset = ds

        # restore the DB
        dbuser = settings.DATABASES['default']['USER']
        passwd = settings.DATABASES['default']['PASSWORD']

        with closing(MySQLdb.connect (host = newproj.host, user = settings.DATABASES['default']['USER'], passwd = settings.DATABASES['default']['PASSWORD'])) as newconn:
          with closing ( newconn.cursor() ) as newcursor:

            # all channel tables have a common prefix with underscore
            sql = "CREATE DATABASE {}".format(newproj.project_name)

            newcursor.execute(sql)

        # upload the backup file to the database
        inputfile = open ( bu.filename )
        cmd = ['mysql', '-u'+ dbuser, '-p'+ passwd, '-h', newproj.host, newproj.project_name ]

        #synchronously or asynchrnously 
        if request.POST.get('async'):

          po_process = subprocess.Popen(cmd, stdin=inputfile)

          # indicate that we are restoring.
          bu.status = 3
          bu.save()

          messages.success(request, 'Initiated restore in background')

          # create a thread to monitor 
          import threading
          t = threading.Thread ( target=_monitorRestore, args=(po_process,newproj,bu,inputfile) )
          t.start()
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/backupproject')

        else:
          po = subprocess.Popen(cmd)
          po.communicate(None)
          rc = po.returncode
          if rc<0:
            raise OCPCAError("Failed to backup file. Status = {}".format(rc))

        # Having restored the database, add the channels, project and token
        newproj.save()
        inputfile.close()

        # default token?
        if 'token' in request.POST:
          tk = Token ( token_name = newproj.project_name, token_description = 'Default token for public project', project_id=newproj, user_id=request.user.id, public=newproj.public ) 
          tk.save()
          
        # is it a single channel backup or a whole project?
        if bu.channel == None:
          chanlist = projmd['channels']
        else: 
          chanlist = [bu.channel]
       
        # Create channels
        for chnm in projmd['channels']:
          ch = Channel()
          ch.project = newproj
          ch.channel_name = chnm
          ch.channel_description = projmd['channels'][chnm]['description']
          ch.channel_type = projmd['channels'][chnm]['channel_type']
          ch.channel_datatype = projmd['channels'][chnm]['datatype']
          ch.resolution = projmd['channels'][chnm]['resolution']
          ch.propagate = projmd['channels'][chnm]['propagate']
          ch.readonly = projmd['channels'][chnm]['readonly']
          ch.exceptions =   projmd['channels'][chnm]['exceptions']
          ch.startwindow = projmd['channels'][chnm]['windowrange'][0]
          ch.endwindow = projmd['channels'][chnm]['windowrange'][1]

          ch.save()

        messages.success(request, 'Sucessfully restored database '+ newproj.project_name)
        return redirect(getProjects)

      if 'createchannel' in request.POST:
        """Add new channel to existing project"""

        #synchronously or asynchrnously 
        if request.POST.get('casync'):

          # set the in process backup state
          bu = Backup.objects.get ( backup_id=request.POST.get("buid") )
          bu.status=3
          bu.save()
          print "Save here in web thread Value = {}".format(bu.status)

          # create a thread to monitor 
          import threading
          t = threading.Thread ( target=_restoreOneChannel, args=(request,) )
          t.start()
          return HttpResponseRedirect(get_script_prefix()+'ocpuser/backupproject')

        else:

          _restoreOneChannel ( request )

        return redirect(getProjects)


      elif 'backtoprojects' in request.POST:
        return redirect(getProjects)

      else: 
        raise OCPCAError ( "Bad post option.  Contact OCP support." )

    else:
      """Show the restore form"""

      buid = request.session["backupid"]

      bu = Backup.objects.get( backup_id=buid )
      pr = Project.objects.get ( project_name = bu.project )
      if bu.channel == None:
        ch = None
      else:
        ch = Channel.objects.get ( project=bu.project, channel_name = bu.channel )
      
      # initialize the forms
      pform = ProjectForm(instance=pr)
      if ch:
        cform = ChannelForm(instance=ch)
      else:
        cform = False  # or None

      filename = bu.filename
      jsonfile = bu.jsonfile

      # get all channel choices
      cprojs = Project.objects.filter(dataset=pr.dataset,user=request.user.id) 

      context = {'cform': cform, 'pform': pform, 'filename': filename, 'buid': buid, 'cprojects': cprojs, 'project_name': pr.project_name}
      return render_to_response('restore.html', context, context_instance=RequestContext(request))

  except Exception, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    return redirect(get_script_prefix()+'ocpuser/projects', {"user":request.user})


def _restoreOneChannel ( request ):
  """Restore on channel.  This can be called directly or in a thread for async"""

  bu = Backup.objects.get ( backup_id=request.POST.get("buid") )
  pr = Project.objects.get ( project_name=request.POST.get("cproject") )
  ds = Dataset.objects.get ( dataset_name=pr.dataset_id )

  jfp = open ( bu.jsonfile ) 
  projmd = json.load ( jfp )

  # old channel name in backup
  oldchnm = bu.channel.channel_name
  oldch = projmd['channels'][bu.channel.channel_name]
  # new channel name specified in form
  chnm = request.POST.get("channel_name") 

  ch = Channel()
  ch.project = pr
  ch.channel_name = chnm
  ch.channel_description = request.POST.get("channel_description")
  ch.channel_type = oldch['channel_type']
  ch.channel_datatype = oldch['datatype']
  ch.resolution = oldch['resolution']
  ch.propagate = oldch['propagate']
  ch.readonly = oldch['readonly']
  ch.exceptions = oldch['exceptions']
  ch.startwindow = oldch['windowrange'][0]
  ch.endwindow = oldch['windowrange'][1]

  # with the project and the channels, restore the channel
  dbuser = settings.DATABASES['default']['USER']
  passwd = settings.DATABASES['default']['PASSWORD']

  with closing(MySQLdb.connect (host = pr.host, user = settings.DATABASES['default']['USER'], passwd = settings.DATABASES['default']['PASSWORD'])) as newconn:
    with closing ( newconn.cursor() ) as newcursor:

      # create a temporary table to house the restore
      dbname = pr.project_name+''.join(random.choice(string.lowercase) for x in range(20))
      sql = "CREATE DATABASE {}".format(dbname)

      newcursor.execute(sql)

      # restore the database to temporary table
      inputfile = open ( bu.filename )
      cmd = ['mysql', '-u'+ dbuser, '-p'+ passwd, '-h', pr.host, dbname ]
      subprocess.Popen(cmd, stdin=inputfile).communicate(None)

      # loop through the tables copying to new channel names.
      # all channel tables have a common prefix with underscore
      sql = "SHOW TABLES in {}".format(dbname)

      newcursor.execute(sql)
      tables = newcursor.fetchall()

      for tbl in tables:

        # Change the prefix from old channel name to new channel name
        newtbl = re.sub ('^{}'.format(oldchnm),'{}'.format(chnm), tbl[0])

        # create a channel in the target db 
        sql = 'CREATE table {}.{} SELECT * FROM {}.{}'.format(pr.project_name,newtbl,dbname,tbl[0])
        newcursor.execute(sql)

      # drop temp database
      sql = 'DROP DATABASE {}'.format(dbname)
      newcursor.execute(sql)

  messages.success(request, 'Sucessfully restored channel: {} to project: {}  '.format(ch.channel_name, ch.project))

  # if it was async, clear the restoring state oon the backup
  if request.POST.get('casync'):
    bu.status=0
    bu.save()

  # having restored the db, save the channel
  ch.save()


def _monitorBackup ( popen_process, backup_model, fh ):
  """Track the state of the backup subprocess and update the required field"""

  # wait for the process to finish
  popen_process.communicate(None)
  rc = popen_process.returncode

  # backup failed  
  if rc<0:
    backup_model.status = 2
  else:
    # update the state
    backup_model.status = 0
  backup_model.save()

  fh.close()

def _monitorRestore ( popen_process, project_model, backup_model, fh ):
  """Track the state of the restore subprocess and update the required field"""

  # wait for the process to finish
  popen_process.communicate(None)
  rc = popen_process.returncode

  # backup failed  
  if rc<0:
    backup_model.status = 5
  else:
    # update the state
    backup_model.status = 0
  backup_model.save()
  project_model.save()

  fh.close()

@login_required(login_url='/ocp/accounts/login/')
def downloadData(request):
  
  try:
    pd = ocpcaproj.OCPCAProjectsDB()
    
    if request.method == 'POST':
      form= dataUserForm(request.POST)
      if form.is_valid():
        curtoken=request.POST.get('token')
        if curtoken=="other":
          curtoken=request.POST.get('other')
          
        format = form.cleaned_data['format']
        resolution = form.cleaned_data['resolution']
        xmin=form.cleaned_data['xmin']
        xmax=form.cleaned_data['xmax']
        ymin=form.cleaned_data['ymin']
        ymax=form.cleaned_data['ymax']
        zmin=form.cleaned_data['zmin']
        zmax=form.cleaned_data['zmax']
        webargs= curtoken+"/"+format+"/"+str(resolution)+"/"+str(xmin)+","+str(xmax)+"/"+str(ymin)+","+str(ymax)+"/"+str(zmin)+","+str(zmax)+"/"
          
        if format=='hdf5':
          return django.http.HttpResponse(ocpcarest.getCutout(webargs), content_type="product/hdf5" )
        elif format=='npz':
          return django.http.HttpResponse(ocpcarest.getCutout(webargs), content_type="product/npz" )
        else:
          return django.http.HttpResponse(ocpcarest.getCutout(webargs), content_type="product/zip" )
          
      else:
        return redirect(downloaddata)
        #return render_to_response('download.html',context_instance=RequestContext(request))
    else:
      # Load Download page with public tokens                                           
      pd = ocpcaproj.OCPCAProjectsDB()
      form = dataUserForm()
      tokens = pd.getPublic ()
      context = {'form': form ,'publictokens': tokens}
      return render_to_response('download.html',context,context_instance=RequestContext(request))
      #return render_to_response('download.html', { 'dts': datasets },context_instance=\
      # RequestContext(request))                                                                
  except OCPCAError, e:
    messages.error(request, "Exception in administrative interface = {}".format(e)) 
    tokens = pd.getPublic ()
    return redirect(downloaddata)
