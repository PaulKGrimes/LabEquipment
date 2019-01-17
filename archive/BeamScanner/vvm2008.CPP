
//
//  Near field scan with vector voltmeter version 2008



#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <dos.h>
#include <string.h>
#include <alloc.h>
#include <complex.h>
#include <conio.h>
#include <stdlib.h>
#include <time.h>
#include "Decl-32.h"
#include "ni488.h"

FILE *file_ptr, *ftable;
char Fdata_name[32], Ftable_name[32];
int vitesse, unidex, vector, Uscan, Vscan, moyen, Ucenter, Vcenter, centering;
unsigned Ustep_size, Vstep_size;
struct time t,s;
double Apeak, Ppeak, Poffset, *Aref, *Pref;
time_t first, second;

void abort ( int erreur, char *msg )
{
  printf ("Error %d : %s\n", erreur, msg );
  exit (1);
}

void ibwt ( int handle, char *commande )
{
  ibwrt ( handle, commande, strlen(commande) );
  if ( iberr ) abort ( iberr, commande );
}

void trigger ( char *cc )
{
	ibwt ( vector, "*TRG" );
	ibwt ( vector, "FETCH?" );
	ibrd ( vector, cc, 32 );
}

void wait_for_stop ( int handle )
{
  char status;
  char buf[40];

  ibrsp ( handle, &status );
  while ( !(status & 64 ) )
  {  trigger ( buf );
	  ibrsp ( handle, &status );
  }
  do {
	ibrsp (handle, &status);
	trigger ( buf );
  } while (status & 64);
}

void print_time (int sum)
{
  double t_time,s_time;

  if (!sum)     /* if this is previous to run */
  {  gettime(&s);
	 printf(" Time : %d:%02d:%02d.%02d\n",s.ti_hour,s.ti_min,s.ti_sec,s.ti_hund);
  }
  else
  {  gettime(&t);
	 printf("\n Time : %d:%02d:%02d.%02d\n",t.ti_hour,t.ti_min,t.ti_sec,t.ti_hund);
	 s_time = 3600*s.ti_hour + s.ti_min*60 + s.ti_sec + .01*s.ti_hund;
	 t_time = 3600*t.ti_hour + t.ti_min*60 + t.ti_sec + .01*t.ti_hund;
	 printf ("Elapsed time is : %2.2lf seconds\n",t_time-s_time);
  }
}

void ms_delay ( unsigned milliseconds )    //delay routine
{
	clock_t  cstart, cend;
	double  Tdiff = 0.0, interval;

	cstart = clock ();
	interval = (double) milliseconds;
	while ( Tdiff < interval )
	{ cend = clock ();
	  Tdiff = ( cend - cstart )/CLK_TCK * 1000.0;
	}
	return;
}

void InvertByte ( char far *buffer, double *dd )
{
	char far *bb,*cc;
	int k;

	bb = &buffer[7];
	cc = (char far*) dd;
	for ( k=0; k<8; ++k, --bb, ++cc ) *cc = *bb;
}

void Measure ( int Average, double *damp, double *dphase )
{
	char buf[40];
	int k;
	double A, theta, aa, phi, xre=0.0, yim=0.0;

  trigger ( buf );
  InvertByte ( &buf[3], &A );
  InvertByte ( &buf[14], &theta);
	for ( k=0; k<Average; ++k )
	{ ms_delay (10);		//include 10 ms delay between data points
	  trigger ( buf );
	  InvertByte ( &buf[3], &A );
	  InvertByte ( &buf[14], &theta );
//          printf("%d %lf %lf\n",k, A, theta);
	  aa = pow (10.0, A/20.0);
	  phi = theta/180.0*M_PI;
          xre += aa*cos(phi);
	  yim += aa*sin(phi);
	}
	xre = xre / Average;
        yim = yim / Average;
	*damp = 10.0*log10(xre*xre+yim*yim);
	*dphase = atan2(yim,xre)/M_PI*180.0;
}

void Rmove ( int xdir, int ydir, int xstep, int ystep )
{
	char instruct[40];
	long step;
	double attente;

  if ( xdir )
  { step = ((long) xstep) * ((long) xdir);
	 sprintf ( instruct, "I U F%d D%ld *", vitesse,step);
	 ibwt ( unidex, instruct );
	 wait_for_stop ( unidex );
	 if ( xdir && ydir )
	 { attente = (double) abs(step);
		attente = attente/vitesse;
		first = time(NULL);
		do
		 second=time(NULL);
		while(difftime(second,first)<((int)floor(attente)));
		step = ((long) ystep) * ((long) ydir);
		sprintf ( instruct, "I V F%d D%ld *", vitesse,step);
		ibwt ( unidex, instruct );
		wait_for_stop ( unidex );
	 }
  }
  else if ( ydir )
  { step = ((long) ystep) * ((long) ydir);
	 sprintf ( instruct, "I V F%d D%ld *", vitesse,step);
	 ibwt ( unidex, instruct );
	 wait_for_stop ( unidex );
    attente = (double) abs(step);
	 attente = attente/vitesse/10.0;
	 first = time(NULL);
	 do
		 second=time(NULL);
	 while(difftime(second,first)<attente);
  }
}

/* void Backup (file *ftable){
	int newx, newy;

	fclose(Foutput);
	printf("\n Please enter new x y positions: ");
	scanf("%d %d", &newx, &newy);
}
*/

void raster ( int mx, int ny, int xstep, int ystep,
				double **damp, double **dphase, int save )
{
  int ix, jy, ii, direction=1, xmiddle, ymiddle;
  double xpos, ypos, f1, f2;
  double far *dp, *dq;

//  mx2 = mx/2;
//  ny2 = ny/2;
  //xmiddle = (mx+1)/2;
  //ymiddle = (ny+1)/2;
  xmiddle = (mx-1)/2;
  ymiddle = (ny-1)/2;
  dp = &f1;
  dq = &f2;
  for ( jy=0; jy<ny; ++jy )
  { for ( ix=0; ix<mx; ++ix )
	 {
		top:
		if (!save)
		{   dp = &damp[jy][ix];
			 dq = &dphase[jy][ix];
		}
		Measure ( moyen, dp, dq );
//    xpos = (ix-mx2+0.5)/200.0*xstep*direction;
//    ypos = (jy-ny2+0.5)/200.0*ystep;
		ypos = (jy-ymiddle)/200.0 * ystep;
		ii = (direction==1) ? ix : mx-ix-1;
//      xpos = (ii-mx2+0.5)/200.0*xstep;
		xpos = (ii-xmiddle)/200.0*xstep;
		if (save)
		{ f1 = f1-Apeak;
		  f2 = f2-Ppeak+Poffset;
		  if ( f2 > 180.0 ) f2 = f2-360.0;
		  else if ( f2 < -180.0 ) f2 = 360.0+f2;
		  fprintf ( file_ptr, "%4d %4d %7.3lf %7.3lf %7.2lf %7.2lf\n",
					ii, jy, xpos, ypos, f1, f2 );
		}
		gotoxy(1,24);
		printf ( "%4d %4d %7.2lf %7.2lf", ii, jy, *dp, *dq );
		if ( ii == xmiddle )
		{ Rmove ( 0, ymiddle-jy, xstep, ystep );
		  Measure ( moyen, &Aref[jy], &Pref[jy] );
		  Aref[jy] = Aref[jy]-Apeak;
		  Pref[jy] = Pref[jy]-Ppeak+Poffset;
//		  if ( g2 > 180.0 ) g2 = g2-360.0;
//		  else if ( g2 < -180.0) g2 = 360.0+g2;
		  printf ( "    Ref > %7.2lf %7.2lf\n", Aref[jy], Pref[jy]);
		  Rmove ( 0, jy-ymiddle, xstep, ystep );
		}

		/* if (getch()=='\k') {
			Backup(ftable, file_ptr);
			goto top;
		}
		*/
		if ( ix != (mx-1) ) Rmove ( direction, 0, xstep, ystep );
	 }
	 direction *= -1;
	 printf("\a");
	 if ( jy != (ny-1) ) Rmove ( 0, 1, xstep, ystep );
  }
}

void Peak_Search ( int mx, int ny, double **damp, int *px, int *py )
{
  int ix, jy;
  double dd,dd0;

  dd0 = damp[0][0];
  *px = -mx;
  *py = -ny;
  for ( jy=-ny; jy<=ny; ++jy )
  { for ( ix=-mx; ix<=mx; ++ix )
	{ if ( (dd =  damp[ny+jy][mx+ix]) > dd0 )
	  { dd0 = dd;
		*px = ix;
		*py = jy;
	  }
	}
  }
}

int v_read ( FILE *fich, char *format,... )
{
  char dstring[132];
  va_list ap;
  int entries;

  if ( fgets(dstring,132,fich) == NULL ) return (0);
  va_start(ap,format);
  entries = vsscanf(dstring,format,ap);
  va_end(ap);
  if ( entries <= 0 ) abort ( entries, "File Read problem" );
  return (entries);
}

void Parameter ()
{
	FILE *fich;
	char ch;
	int ang;

	fich = fopen ( "scan2.use", "r" );
	if ( fich == NULL ) abort ( 1, "Use File not opened" );
	if ( !v_read ( fich, "%s", Fdata_name ) ) abort ( 2, "no o/p data file" );
	file_ptr = fopen ( Fdata_name, "w" );
	if ( file_ptr == NULL ) abort ( 3, "o/p file not opened" );
	if ( v_read ( fich, "%d %d", &Uscan, &Vscan ) != 2 ) abort ( 4, "Data not read" );
	Aref = (double*) malloc(Vscan*sizeof(double));
	Pref = (double*) malloc(Vscan*sizeof(double));

	if ( v_read ( fich, "%u %u", &Ustep_size, &Vstep_size ) != 2 )
		abort ( 5, "data not read" );
	Ustep_size = Ustep_size/5;           // step size in 5 microns
	Vstep_size = Vstep_size/5;
	if ( v_read ( fich, "%d", &moyen ) != 1 ) abort ( 6, "data not read" );
	if ( v_read ( fich, "%d %d", &Ucenter, &Vcenter ) != 2 )
		abort ( 7, "data not read" );
	if ( v_read ( fich, "%d", &vitesse ) != 1 ) abort ( 8, "data not read");
	if ( v_read ( fich, "%c", &ch ) != 1 ) abort ( 9, "data not read");
	if ( v_read ( fich, "%d", &ang ) != 1 ) abort ( 10, "integer angle needed" );
	Poffset = ang;
	centering = ( (ch=='c') || (ch=='C') ) ? 1 : 0;
	if ( !v_read(fich, "%s", Ftable_name) ) abort(11,"no table file");

	fclose ( fich );
}

void Init_vector ()
{
	if ( (vector = ibdev(0, 8, 0, T10s, 1, 0)) < 0 ) abort ( 11, "Vector voltmeter not found!" );
	ibwt ( vector, "SENSE TRANSMISSION");
	ibwt ( vector, "FORMAT LOG");
	ibwt ( vector, "TRIG SOUR:BUS" );
	ibwt ( vector, "DISP:STAT OFF" );
	ibwt ( vector, "SYST:FORM FP64" );
}

void main ( )
{
  double far **amp, **phase;
  int kx, ky;

  clrscr();
  printf("Reading .use file...\n");
  Parameter ( );
  printf("Initializing...\n");

  if ( (unidex = ibdev(0, 2, 0, T10s, 1, 0)) < 0 ) abort ( 12, "Scanner not found!" );

  ibwt (unidex, "O" ); /* O - untriggered mode */
  ibwt (unidex, "J" );
  Init_vector ();
  printf ("instrument initialized\n");

  if ( centering )
  { Rmove ( -Ucenter, -Vcenter, Ustep_size/2, Vstep_size/2 );
	 raster ( 2*Ucenter+1, 2*Vcenter+1, Ustep_size/2, Vstep_size/2, amp, phase, 0 );
	 Peak_Search( Ucenter, Vcenter, amp, &kx, &ky );
	 Rmove ( kx-Ucenter, ky-Vcenter, Ustep_size/2, Vstep_size/2 );
  }
  Measure ( moyen, &Apeak, &Ppeak );
  first=time(NULL);
  do
		second=time(NULL);
  while(difftime(second,first)<1);

  Measure ( 4*moyen, &Apeak, &Ppeak );
  Rmove ( -(Uscan-1), -(Vscan-1), Ustep_size/2, Vstep_size/2 );
  print_time(0);
  raster ( Uscan, Vscan, Ustep_size, Vstep_size, amp, phase, 1 );
  print_time(1);
  if ( Uscan % 2 ) Rmove ( -(Uscan-1), -(Vscan-1), Ustep_size/2, Vstep_size/2 );
  else Rmove ( (Uscan-1), -(Vscan-1), Ustep_size/2, Vstep_size/2 );

  fclose (file_ptr);            /* closes output file */
	ftable = fopen ( Ftable_name, "w" );
	if ( ftable == NULL ) abort ( 12, "table file not open!" );

  for ( ky=0; ky<Vscan; ++ky )
		fprintf ( ftable, "%4d %7.2lf %7.2lf\n", ky, Aref[ky], Pref[ky] );
  fclose ( ftable );
  first=time(NULL);
  do
		second=time(NULL);
  while(difftime(second,first)<5);

  printf ("Scanning is terminated.\n");
  do
		second=time(NULL);
  while(difftime(second,first)<5);

  ibwrt ( unidex, "C", 1);        // resets Unidex

  printf("\n Press 'e' to exit.");
  do
	  if (getch()=='e') break;
  while(1==1);
}

