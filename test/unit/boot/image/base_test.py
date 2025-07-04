import io
from collections import namedtuple
from unittest.mock import (
    patch, Mock, MagicMock
)
from pytest import raises

from kiwi.boot.image.base import BootImageBase
from kiwi.defaults import Defaults

from kiwi.exceptions import (
    KiwiTargetDirectoryNotFound,
    KiwiConfigFileNotFound,
    KiwiDiskBootImageError
)


class TestBootImageBase:
    @patch('kiwi.boot.image.base.os.path.exists')
    def setup(self, mock_exists):
        Defaults.set_platform_name('x86_64')
        self.boot_names_type = namedtuple(
            'boot_names_type', [
                'kernel_name', 'initrd_name',
                'kernel_version', 'kernel_filename'
            ]
        )
        self.kernel = Mock()
        kernel_info = Mock
        kernel_info.name = 'kernel_name'
        kernel_info.version = 'kernel_version'
        kernel_info.filename = 'kernel_filename'
        self.kernel.get_kernel.return_value = kernel_info
        self.boot_xml_state = Mock()
        self.xml_state = Mock()
        self.xml_state.get_initrd_system = Mock(
            return_value='dracut'
        )
        self.xml_state.xml_data.get_name = Mock(
            return_value='some-image'
        )
        self.xml_state.get_image_version = Mock(
            return_value='1.2.3'
        )
        self.xml_state.build_type.get_boot = Mock(
            return_value='oemboot/suse-13.2'
        )
        mock_exists.return_value = True
        self.boot_image = BootImageBase(
            self.xml_state, 'some-target-dir', 'system-directory'
        )

    @patch('kiwi.boot.image.base.os.path.exists')
    def setup_method(self, cls, mock_exists):
        self.setup()

    def test_boot_image_raises(self):
        with raises(KiwiTargetDirectoryNotFound):
            BootImageBase(
                self.xml_state, 'target-dir-does-not-exist', 'some-root-dir'
            )

    def test_prepare(self):
        with raises(NotImplementedError):
            self.boot_image.prepare()

    def test_create_initrd(self):
        with raises(NotImplementedError):
            self.boot_image.create_initrd()

    def test_create_uki(self):
        with raises(NotImplementedError):
            self.boot_image.create_uki('some_cmdline')

    @patch('os.listdir')
    def test_is_prepared(self, mock_listdir):
        mock_listdir.return_value = []
        assert self.boot_image.is_prepared() is False
        mock_listdir.return_value = ['a', 'b', 'c']
        assert self.boot_image.is_prepared() is True

    @patch('kiwi.boot.image.base.XMLState.copy_strip_sections')
    def test_import_system_description_elements(self, mock_strip):
        self.boot_image.import_system_description_elements()
        assert self.xml_state.copy_displayname.called
        assert self.xml_state.copy_name.called
        assert self.xml_state.copy_repository_sections.called
        assert self.xml_state.copy_drivers_sections.called
        assert mock_strip.called
        assert self.xml_state.copy_strip_sections.called
        assert self.xml_state.copy_preferences_subsections.called
        assert self.xml_state.copy_bootincluded_packages.called
        assert self.xml_state.copy_bootincluded_archives.called
        assert self.xml_state.copy_bootdelete_packages.called
        assert self.xml_state.copy_build_type_attributes.called
        assert self.xml_state.copy_systemdisk_section.called
        assert self.xml_state.copy_machine_section.called
        assert self.xml_state.copy_oemconfig_section.called

    def test_get_boot_description_directory(self):
        assert self.boot_image.get_boot_description_directory() == \
            '/usr/share/kiwi/custom_boot/oemboot/suse-13.2'

    @patch('kiwi.boot.image.base.BootImageBase.get_boot_description_directory')
    def test_load_boot_xml_description(self, mock_boot_dir):
        mock_boot_dir.return_value = None
        with raises(KiwiConfigFileNotFound):
            self.boot_image.load_boot_xml_description()

    @patch('kiwi.boot.image.base.Kernel')
    def test_get_boot_names_raises(self, mock_Kernel):
        kernel = Mock()
        mock_Kernel.return_value = kernel
        kernel.get_kernel.return_value = None
        with raises(KiwiDiskBootImageError):
            self.boot_image.get_boot_names()

    @patch('kiwi.boot.image.base.Kernel')
    def test_get_boot_names_with_initrd_system_set_to_none(self, mock_Kernel):
        kernel = Mock()
        mock_Kernel.return_value = kernel
        kernel.get_kernel.return_value = None
        self.xml_state.get_initrd_system.return_value = 'none'
        boot_names = self.boot_image.get_boot_names()
        assert boot_names.kernel_name == 'none'
        assert boot_names.initrd_name == 'none'
        assert boot_names.kernel_version == 'none'

    @patch('kiwi.boot.image.base.Kernel')
    @patch('kiwi.boot.image.base.Path.which')
    @patch('kiwi.boot.image.base.log.warning')
    @patch('glob.iglob')
    def test_get_boot_names_default(
        self, mock_iglob, mock_warning, mock_Path_which, mock_Kernel
    ):
        mock_iglob.return_value = []
        mock_Path_which.return_value = None
        mock_Kernel.return_value = self.kernel
        self.xml_state.get_initrd_system.return_value = 'kiwi'
        assert self.boot_image.get_boot_names() == self.boot_names_type(
            kernel_name='kernel_name',
            initrd_name='initrd-kernel_version',
            kernel_version='kernel_version',
            kernel_filename='kernel_filename'
        )
        self.xml_state.get_initrd_system.return_value = 'dracut'
        assert self.boot_image.get_boot_names() == self.boot_names_type(
            kernel_name='kernel_name',
            initrd_name='initramfs-kernel_version.img',
            kernel_version='kernel_version',
            kernel_filename='kernel_filename'
        )

    @patch('kiwi.boot.image.base.Kernel')
    @patch('kiwi.boot.image.base.Path.which')
    @patch('kiwi.boot.image.base.log.warning')
    @patch('glob.iglob')
    @patch('os.path.islink')
    def test_get_boot_names_from_file(
        self, mock_islink, mock_iglob, mock_warning, mock_Path_which,
        mock_Kernel
    ):
        mock_islink.return_value = False
        mock_iglob.return_value = [
            '/boot/initrd.img-kernel_version'
        ]
        mock_Path_which.return_value = None
        mock_Kernel.return_value = self.kernel
        self.xml_state.get_initrd_system.return_value = 'dracut'
        assert self.boot_image.get_boot_names() == self.boot_names_type(
            kernel_name='kernel_name',
            initrd_name='initrd.img-kernel_version',
            kernel_version='kernel_version',
            kernel_filename='kernel_filename'
        )

    @patch('kiwi.boot.image.base.Kernel')
    @patch('kiwi.boot.image.base.Path.which')
    @patch('kiwi.boot.image.base.log.warning')
    @patch('glob.iglob')
    def test_get_boot_names_from_dracut(
        self, mock_iglob, mock_warning, mock_Path_which, mock_Kernel
    ):
        mock_iglob.return_value = []
        mock_Path_which.return_value = 'dracut'
        mock_Kernel.return_value = self.kernel
        self.xml_state.get_initrd_system.return_value = 'dracut'
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = 'outfile="/boot/initrd-$kernel"'
            assert self.boot_image.get_boot_names() == self.boot_names_type(
                kernel_name='kernel_name',
                initrd_name='initrd-kernel_version',
                kernel_version='kernel_version',
                kernel_filename='kernel_filename'
            )
            file_handle.read.return_value = 'outfile="/boot/initrd-${kernel}"'
            assert self.boot_image.get_boot_names() == self.boot_names_type(
                kernel_name='kernel_name',
                initrd_name='initrd-kernel_version',
                kernel_version='kernel_version',
                kernel_filename='kernel_filename'
            )

    def test_noop_methods(self):
        self.boot_image.include_module('module')
        self.boot_image.omit_module('module')
        self.boot_image.set_static_modules(['module'])
        self.boot_image.include_driver('driver')
        self.boot_image.omit_driver('driver')
        self.boot_image.write_system_config_file({'config_key': 'value'})
        self.boot_image.cleanup()

    def test_has_initrd_support(self):
        assert self.boot_image.has_initrd_support() is False

    def test_add_argument(self):
        assert self.boot_image.add_argument('some') is None
