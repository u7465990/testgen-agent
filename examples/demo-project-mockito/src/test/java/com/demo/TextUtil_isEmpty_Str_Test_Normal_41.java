package com.demo;

import com.demo.TextUtil;
import org.junit.Test;
import org.junit.Assert.*;

public class TextUtil_isEmpty_Str_Test_Normal_41 {


    @Test
    public void testIsEmptyWithRepresentativeInputs() {
        boolean resultNonEmpty = TextUtil.isEmpty("test");
        boolean resultEmpty = TextUtil.isEmpty("");

        org.junit.Assert.assertFalse("A non-empty string should not be considered empty", resultNonEmpty);
        org.junit.Assert.assertTrue("An empty string should be considered empty", resultEmpty);
    }

}
