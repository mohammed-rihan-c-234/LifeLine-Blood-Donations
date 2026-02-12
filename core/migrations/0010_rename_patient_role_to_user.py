from django.db import migrations


def rename_patient_role(apps, schema_editor):
    User = apps.get_model('core', 'User')
    User.objects.filter(role='patient').update(role='user')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_set_donor_availability_available'),
    ]

    operations = [
        migrations.RunPython(rename_patient_role, noop_reverse),
    ]

