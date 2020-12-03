from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('user', '0001_initial'),
        ('book', '0002_auto_20201203_0053'),
    ]

    operations = [
        migrations.CreateModel(
            name='Library',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=45)),
                ('image_url', models.URLField()),
            ],
            options={
                'db_table': 'libraries',
            },
        ),
        migrations.CreateModel(
            name='LibraryBook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='book.book')),
                ('library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='library.library')),
            ],
            options={
                'db_table': 'library_books',
            },
        ),
        migrations.AddField(
            model_name='library',
            name='books',
            field=models.ManyToManyField(through='library.LibraryBook', to='book.Book'),
        ),
        migrations.AddField(
            model_name='library',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user'),
        ),
    ]
