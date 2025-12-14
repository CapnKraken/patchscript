" Syntax highlighting for Patchscript .patch files in Vim

" FYI:
" If you're using git bash with its default vimrc, it'll think .patch files
" are 'diff' files, and this highlighting won't apply. 

if exists("b:current_syntax")
	finish
endif

let b:current_syntax = "patch"
		
" Why not have todos? These are case-sensitive.
syn keyword pTodo contained TODO FIXME NOTE

syntax case ignore

" Comments start with # and continue to the end of the line
" '#' must be the first non-whitespace character in the line for it to work
syn match pComment "^\s*#.*$" contains=pTodo

" multiline comments start with #= and end with =#
" However, '#=' or '=#' must be the first non-whitespace words on their lines
" Additionally, all text after '=#' will still be commented
syn region pComment start="^\s*#=" end="=#.*$" contains=pTodo fold

" Manually create folding regions using ##/#- or #region/#endregion
syn region pCommentRegion start="^\s*##\|^\s*#\s\?region" end="^\s*#-.*$\|^\s*#\s\?endregion.*$" contains=ALL fold keepend extend

" Strings can't be multiline but idk how to make it not highlight that yet
syn region pString start='"' end='"'

" KEYWORDS

" The main bounds for script segments
syn keyword pMainStart start receive trap
syn keyword pMainEnd end

hi def link pMainStart pMain
hi def link pMainEnd pMain
" could not get this to work so just commented out for now
"syn region pFoldMain start="^\s*start\|^\s*receive\|^\s*trap" end="^\s*end" contains=ALL fold keepend

" Other bounds for code segments: loops and conditions
syn keyword pFoldTop if loop while repeat 
syn keyword pFoldMid elif else
syn keyword pFoldEnd endif endloop endwhile endrepeat

hi def link pFoldEnd pFold
hi def link pFoldMid pFold
hi def link pFoldTop pFold

" Keyword operators followed by symbol operators
syn keyword pOperator and or not
syn keyword pOperator lower upper abs round
syn keyword pOperator int float str eval
syn keyword pTrig sin cos tan arcsin arccos arctan
syn match pOperator "[+\-\*/%`=<>!\^&|~]"

hi def link pTrig pOperator

" Numbers
syn match pNum "\(\w\)\@1<!\-\?[0-9\.]\+"

" Builtin variables start with _underscore
" You can define your own variables with _
" to have them highlight differently
syn match pBuiltin "\(\w\)\@<!_\w*"

" Highlight function definitions and function calls as functions
syn keyword pFunction return 
syn match pFunction "def \w*"
syn match pFunction "{\zs\w*"

" Highlight the entire include line
" TODO highlight everything after 'include' as a string
syn match pInclude "include .*"

" Assignment statements
syn keyword pAssign set setvar setattribute setglob setindex
" Positioning
syn keyword pMotion setposition translate move
" Array and str ops
syn keyword pList string join split merge append remove insert copy
" Collision assignment
syn keyword pSetcol setmask setcollider

hi def link pMotion pAssign
hi def link pList 	pAssign
hi def link pSetcol pAssign

" Script control
syn keyword pLabel label 
syn keyword pControl stopscripts stopall delete instance fork jump callstack
syn keyword pControl adopt kidnap changelayer wait broadcast unicast

hi def link pLabel pControl

" Function-like statements
syn keyword pFunction random angle distance collide maskcollide getkey
syn keyword pFunction getattribute getglob getindex

" Output statements
syn keyword pSprite setsprite updatesprite colorshift sprite canvas
syn keyword pDraw draw stamp text clear rect ellipse polygon line
syn keyword pFile load unload file font sound music
syn keyword pOutput log

hi def link pSprite pOutput
hi def link pDraw pOutput
hi def link pFile pOutput

" Configuration statements
syn keyword pConfig configure apply caption hide_mouse window_size
syn keyword pConfig target_framerate screen_resolution fullscreen

hi def link pComment			Comment
hi def link pString				String
hi def link pFold				Conditional
hi def link pMain				Statement
hi def link pFunction 			Function
hi def link pOperator 			Operator
hi def link pBuiltin			SpecialChar
hi def link pNum 				Number
hi def link pTodo				Todo
hi def link pInclude			Include
hi def link pConfig				PreProc
hi def link pAssign 			Constant
hi def link pControl			Repeat
hi def link pOutput				Type
" No macros yet but maybe in the future
hi def link pMacro				Macro

hi def link pStorage 			StorageClass
hi def link pError				Error

hi Comment term=italic cterm=italic

syn sync fromstart
