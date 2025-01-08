# Generated by Django 5.1.4 on 2025-01-04 01:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0002_proyecto_empleados'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='encargado',
            field=models.ForeignKey(blank=True, limit_choices_to={'rol': 'encargado'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='empleados', to='gestion.usuario'),
        ),
    ]